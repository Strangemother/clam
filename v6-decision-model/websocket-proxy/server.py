#!/usr/bin/env python3
"""Forward WebSocket JSON messages to a decision-model HTTP endpoint."""

import argparse
import asyncio
from functools import partial
import json
import os
from pathlib import Path
import sys

from websockets.asyncio.server import serve
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chromites import Chromite
from tools import make_headers, request_json


async def handle_client(websocket, base_url):
    try:
        chromite = Chromite(websocket, websocket.request.path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        await websocket.send(json.dumps({"error": str(exc)}))
        await websocket.close(code=1008, reason="Could not load prompt")
        return

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
                finally:
                    await chromite._flush_client_sends()
                if not isinstance(payload, dict):
                    raise ValueError("Message hook must return a JSON object.")
                response = await asyncio.to_thread(
                    request_json,
                    f"{base_url}/v1/systemone",
                    make_headers(),
                    payload,
                )
            except (ValueError, UnicodeDecodeError, RuntimeError) as exc:
                response = {"error": str(exc)}
            await websocket.send(json.dumps(response))
    finally:
        chromite.on_close()


async def run_server(base_url):
    async with serve(
        partial(handle_client, base_url=base_url),
        "localhost",
        9999,
    ):
        print("Listening on ws://localhost:9999/<prompt-name>/", flush=True)
        await asyncio.Future()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "LM_STUDIO_BASE_URL", "http://192.168.50.60:1234"
        ),
        help="decision-model HTTP server URL",
    )
    args = parser.parse_args()
    asyncio.run(run_server(args.base_url.rstrip("/")))


if __name__ == "__main__":
    main()
