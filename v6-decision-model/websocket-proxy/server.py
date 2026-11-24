#!/usr/bin/env python3
"""Forward WebSocket JSON messages to a decision-model HTTP endpoint."""

import argparse
import asyncio
from functools import partial
import inspect
import json
import os
from pathlib import Path
import sys

from websockets.asyncio.server import serve
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chromites import Chromite
import settings


MAX_MESSAGE_BYTES = settings.MAX_MESSAGE_BYTES


async def handle_client(websocket, base_url):
    try:
        chromite = Chromite(websocket, websocket.request.path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        await websocket.send(json.dumps({"error": str(exc)}))
        await websocket.close(code=1008, reason="Could not load prompt")
        return

    chromite.base_url = base_url.rstrip("/")
    try:
        chromite.on_create()
        await chromite._flush_client_sends()
        async for message in websocket:
            try:
                payload = json.loads(message)
                if not isinstance(payload, dict):
                    raise ValueError("Request must be a JSON object.")
                try:
                    payload = chromite.on_message(payload)
                    if inspect.isawaitable(payload):
                        payload = await payload
                finally:
                    await chromite._flush_client_sends()
                if payload is None:
                    continue
                if not isinstance(payload, dict):
                    raise ValueError(
                        "Message hook must return a JSON object or None."
                    )
                response = await chromite.request_model(payload)
            except (ValueError, UnicodeDecodeError, RuntimeError) as exc:
                response = {"error": str(exc)}
            await websocket.send(json.dumps(response))
    finally:
        chromite.on_close()


async def run_server(base_url):
    async with serve(
        partial(handle_client, base_url=base_url),
        settings.HOST,
        settings.PORT,
        max_size=MAX_MESSAGE_BYTES,
    ):
        print(
            f"Listening on {settings.HOST}:{settings.PORT} "
            "(path: /<prompt-name>/)",
            flush=True,
        )
        await asyncio.Future()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "LM_STUDIO_BASE_URL", settings.DECISION_MODEL_ENDPOINT
        ),
        help="decision-model HTTP server URL",
    )
    args = parser.parse_args()
    asyncio.run(run_server(args.base_url.rstrip("/")))


if __name__ == "__main__":
    main()
