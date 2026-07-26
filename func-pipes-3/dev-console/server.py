"""Run a tiny WebSocket fake backend and serve its browser console."""

from __future__ import annotations

import argparse
import asyncio
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from websockets.asyncio.server import serve


class DevBackend:
    """Broadcast opaque messages to every connected development client."""

    def __init__(self) -> None:
        self.clients: set[Any] = set()

    async def handle(self, websocket: Any) -> None:
        self.clients.add(websocket)
        await websocket.send(json.dumps({"kind": "server", "name": "connected"}))
        try:
            async for message in websocket:
                await self.broadcast(message)
        finally:
            self.clients.discard(websocket)

    async def broadcast(self, message: str | bytes) -> None:
        clients = tuple(self.clients)
        if clients:
            await asyncio.gather(
                *(client.send(message) for client in clients),
                return_exceptions=True,
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Func Pipes dev backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", default=8001, type=int)
    parser.add_argument("--ws-port", default=8778, type=int)
    return parser.parse_args()


def serve_page(host: str, port: int, directory: Path) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Dev console: http://{host}:{port}/")
    try:
        server.serve_forever()
    finally:
        server.server_close()


async def serve_socket(host: str, port: int) -> None:
    backend = DevBackend()
    print(f"Dev WebSocket: ws://{host}:{port}/")
    async with serve(backend.handle, host, port):
        await asyncio.Future()


def main() -> None:
    args = parse_args()
    directory = Path(__file__).resolve().parent
    http_thread = threading.Thread(
        target=serve_page,
        args=(args.host, args.http_port, directory),
        daemon=True,
    )
    http_thread.start()
    try:
        asyncio.run(serve_socket(args.host, args.ws_port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()