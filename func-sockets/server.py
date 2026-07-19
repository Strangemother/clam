"""Run Func Sockets as an independent WebSocket process.

This file adapts real network connections to :class:`relay.GraphRelay`. Start
it directly or through the installed ``func-sockets`` command::

    python server.py --host 0.0.0.0 --port 8777

Application code normally connects to the running service; it does not import
this module. Import :func:`run_server` only when embedding the development
relay in another async launcher or test.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.server import serve

from relay import GraphRelay, graph_id_from_path


LOG = logging.getLogger("func-sockets")


def connection_path(websocket: Any) -> str:
    """Return the request path used to open a WebSocket connection.

    The path is passed to ``graph_id_from_path`` to support URL-based binding.

    Example::

        path = connection_path(websocket)  # "/graph/demo"
    """
    request = getattr(websocket, "request", None)
    return getattr(request, "path", "") or ""


async def handle_connection(websocket: Any, relay: GraphRelay) -> None:
    """Serve one socket until it disconnects.

    The handler binds from the URL when possible, forwards each incoming
    message to the relay, and always removes the socket on exit.

    Example::

        await handle_connection(websocket, relay)
    """
    graph_id = graph_id_from_path(connection_path(websocket))
    if graph_id is not None:
        relay.bind(websocket, graph_id)
        await websocket.send(json.dumps({"type": "bound", "graph_id": graph_id}))

    try:
        async for message in websocket:
            await relay.receive(websocket, message)
    finally:
        relay.unbind(websocket)


async def run_server(host: str, port: int) -> None:
    """Run one relay server until the task is cancelled.

    Example::

        asyncio.run(run_server("127.0.0.1", 8777))
    """
    relay = GraphRelay()

    async def handler(websocket: Any) -> None:
        """Pass one accepted WebSocket connection to the shared relay."""
        await handle_connection(websocket, relay)

    LOG.info("graph relay listening on ws://%s:%d", host, port)
    LOG.info("bind by URL: ws://%s:%d/graph/<graph_id>", host, port)
    async with serve(handler, host, port):
        await asyncio.Future()


def parse_args() -> argparse.Namespace:
    """Parse server host, port, and log level from command-line arguments."""
    parser = argparse.ArgumentParser(description="Minimal graph-scoped WebSocket relay")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8777, help="Bind port")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args()


def main() -> None:
    """Configure logging and run the command-line relay process.

    Example from a shell::

        func-sockets --port 8777 --log-level DEBUG
    """
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_server(args.host, args.port))
    except KeyboardInterrupt:
        LOG.info("shutting down")


if __name__ == "__main__":
    main()
