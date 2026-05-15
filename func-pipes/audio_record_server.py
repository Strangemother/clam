#!/usr/bin/env python3
"""Standalone WebSocket audio recorder service.

The browser recorder node connects directly to this service instead of routing
audio through Flask. The protocol is intentionally small:

Client -> server
  {"type":"start","sample_rate":48000,"channels":1,"sample_width":2,
   "prefix":"mic-record"}
  <binary PCM16 chunks>
  {"type":"stop"}

Server -> client
  {"type":"started","session_id":"..."}
  {"type":"saved","path":"...","public_url":"...",...}
  {"type":"error","message":"..."}

Files are written as WAV under the configured output directory. When that
directory lives under func-pipes/static, a public URL is also returned so the
prompting UI can play the saved recording immediately.
"""

import argparse
import asyncio
import json
import logging
import uuid
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import websockets
except ImportError as exc:  # pragma: no cover - startup guard
    raise ImportError(
        "websockets is required for audio_record_server.py. "
        "Install it with: pip install websockets"
    ) from exc


LOG = logging.getLogger("audio-record-server")


def _sanitize_token(value: Optional[str], default: str) -> str:
    text = (value or "").strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in text)
    cleaned = cleaned.strip("-")
    return cleaned or default


def _build_filename(prefix: str) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return "%s-%s-%s.wav" % (prefix, stamp, suffix)


def _build_public_url(path: Path, static_dir: Path, public_prefix: str) -> Optional[str]:
    try:
        relative = path.resolve().relative_to(static_dir.resolve())
    except ValueError:
        return None

    prefix = "/" + public_prefix.strip("/")
    return prefix.rstrip("/") + "/" + relative.as_posix()


class RecordingSession:
    def __init__(self, output_dir: Path, static_dir: Path, public_prefix: str):
        self.output_dir = output_dir
        self.static_dir = static_dir
        self.public_prefix = public_prefix
        self.reset()

    def reset(self) -> None:
        self.session_id = uuid.uuid4().hex
        self.prefix = "mic-record"
        self.sample_rate = 48000
        self.channels = 1
        self.sample_width = 2
        self.chunks = []  # type: List[bytes]
        self.bytes_received = 0
        self.started = False

    def begin(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.started:
            raise ValueError("recording already started")

        sample_rate = int(payload.get("sample_rate") or 48000)
        channels = int(payload.get("channels") or 1)
        sample_width = int(payload.get("sample_width") or 2)
        prefix = _sanitize_token(payload.get("prefix"), "mic-record")

        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if channels <= 0:
            raise ValueError("channels must be positive")
        if sample_width <= 0:
            raise ValueError("sample_width must be positive")

        self.session_id = str(payload.get("session_id") or uuid.uuid4().hex)
        self.prefix = prefix
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.chunks = []
        self.bytes_received = 0
        self.started = True

        return {
            "type": "started",
            "session_id": self.session_id,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
        }

    def append(self, chunk: bytes) -> None:
        if not self.started:
            raise ValueError("start must be sent before binary audio chunks")
        if not chunk:
            return

        self.chunks.append(chunk)
        self.bytes_received += len(chunk)

    def finalize(self) -> Dict[str, Any]:
        if not self.started:
            raise ValueError("no active recording")
        if not self.bytes_received:
            raise ValueError("no audio data received")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = _build_filename(self.prefix)
        path = (self.output_dir / filename).resolve()
        payload = b"".join(self.chunks)

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(payload)

        frame_bytes = self.channels * self.sample_width
        frame_count = int(len(payload) / frame_bytes) if frame_bytes else 0
        duration_seconds = float(frame_count) / float(self.sample_rate) if self.sample_rate else 0.0
        public_url = _build_public_url(path, self.static_dir, self.public_prefix)

        result = {
            "type": "saved",
            "session_id": self.session_id,
            "path": str(path),
            "filename": filename,
            "public_url": public_url,
            "bytes": self.bytes_received,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
            "frame_count": frame_count,
            "duration_seconds": round(duration_seconds, 3),
        }
        self.reset()
        return result


async def _send_json(websocket: Any, payload: Dict[str, Any]) -> None:
    await websocket.send(json.dumps(payload))


async def handle_client(
    websocket: Any,
    _path: Optional[str] = None,
    output_dir: Optional[Path] = None,
    static_dir: Optional[Path] = None,
    public_prefix: str = "/static/recordings",
) -> None:
    session = RecordingSession(output_dir or Path.cwd(), static_dir or Path.cwd(), public_prefix)

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                try:
                    session.append(message)
                except ValueError as exc:
                    await _send_json(websocket, {"type": "error", "message": str(exc)})
                continue

            try:
                payload = json.loads(message)
            except json.JSONDecodeError as exc:
                await _send_json(websocket, {"type": "error", "message": "invalid JSON: %s" % exc})
                continue

            msg_type = str(payload.get("type") or "").strip().lower()

            if msg_type == "start":
                try:
                    reply = session.begin(payload)
                except ValueError as exc:
                    await _send_json(websocket, {"type": "error", "message": str(exc)})
                else:
                    await _send_json(websocket, reply)
                continue

            if msg_type == "stop":
                try:
                    reply = session.finalize()
                except ValueError as exc:
                    await _send_json(websocket, {"type": "error", "message": str(exc)})
                else:
                    await _send_json(websocket, reply)
                continue

            if msg_type == "cancel":
                session.reset()
                await _send_json(websocket, {"type": "cancelled"})
                continue

            if msg_type == "ping":
                await _send_json(websocket, {"type": "pong"})
                continue

            await _send_json(websocket, {"type": "error", "message": "unknown message type: %s" % msg_type})

    except Exception as exc:  # pragma: no cover - network/runtime variability
        LOG.debug("client disconnected: %s", exc)
    finally:
        if session.started and session.bytes_received:
            try:
                result = session.finalize()
            except Exception as exc:  # pragma: no cover - best effort on disconnect
                LOG.warning("failed to auto-save partial recording: %s", exc)
            else:
                LOG.info("auto-saved partial recording to %s", result.get("path"))


async def serve(host: str, port: int, output_dir: Path, static_dir: Path, public_prefix: str) -> None:
    async def _handler(websocket: Any, path: Optional[str] = None) -> None:
        await handle_client(
            websocket,
            path,
            output_dir=output_dir,
            static_dir=static_dir,
            public_prefix=public_prefix,
        )

    LOG.info("Audio recorder listening on ws://%s:%d", host, port)
    LOG.info("Writing WAV files to %s", output_dir)
    async with websockets.serve(_handler, host, port, max_size=None):
        await asyncio.Future()


def parse_args() -> argparse.Namespace:
    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"
    output_dir = static_dir / "recordings"

    parser = argparse.ArgumentParser(description="Standalone websocket audio recorder")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", default=8766, type=int, help="Bind port")
    parser.add_argument(
        "--output-dir",
        default=str(output_dir),
        help="Directory where WAV files are written",
    )
    parser.add_argument(
        "--static-dir",
        default=str(static_dir),
        help="Static root used to compute a browser-playable public_url",
    )
    parser.add_argument(
        "--public-prefix",
        default="/static/recordings",
        help="Browser path prefix that maps to the output directory when it sits under the static dir",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    output_dir = Path(args.output_dir).expanduser().resolve()
    static_dir = Path(args.static_dir).expanduser().resolve()

    try:
        asyncio.run(serve(args.host, args.port, output_dir, static_dir, args.public_prefix))
    except KeyboardInterrupt:
        LOG.info("shutting down")


if __name__ == "__main__":
    main()