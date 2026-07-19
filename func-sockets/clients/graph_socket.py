"""Reusable Python client for a single Func Sockets graph room.

Use :class:`GraphSocket` in the Python graph process to publish events and
receive UI commands without handling WebSocket setup in graph code.

Minimal use::

    async with GraphSocket("graph-42") as socket:
        await socket.send({"kind": "event", "name": "graph.idle"})
        command = await socket.receive()
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed


class GraphSocket:
    """Connect a Python producer or consumer to one graph room.

    The context manager opens the connection, waits for the server's binding
    confirmation, and closes cleanly when the block exits.
    """

    def __init__(self, graph_id: str, base_url: str = "ws://127.0.0.1:8777") -> None:
        """Prepare a client URL for ``graph_id`` without connecting yet.

        Example::

            socket = GraphSocket("demo", "ws://127.0.0.1:8777")
        """
        self.url = f"{base_url.rstrip('/')}/graph/{quote(graph_id, safe='')}"
        self.websocket = None

    async def __aenter__(self) -> GraphSocket:
        """Open the socket and return this bound client.

        Prefer ``async with GraphSocket("demo") as socket`` over calling this
        method directly.
        """
        self.websocket = await connect(self.url)
        await self.websocket.recv()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close the socket when leaving its ``async with`` block."""
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None

    async def send(self, message: str | bytes | dict[str, Any]) -> None:
        """Send text, bytes, or a JSON-serializable dictionary to graph peers.

        Example::

            await socket.send({"kind": "event", "name": "node.updated"})
        """
        if self.websocket is None:
            raise RuntimeError("GraphSocket is not connected")
        if isinstance(message, dict):
            message = json.dumps(message)
        await self.websocket.send(message)

    async def receive(self) -> str | bytes:
        """Wait for and return the next message from another graph peer.

        JSON remains encoded text so the graph can choose its own decoder.

        Example::

            raw_command = await socket.receive()
        """
        if self.websocket is None:
            raise RuntimeError("GraphSocket is not connected")
        return await self.websocket.recv()

    def __aiter__(self) -> GraphSocket:
        """Return this client as an async stream of incoming messages."""
        return self

    async def __anext__(self) -> str | bytes:
        """Return the next message, ending iteration after socket closure.

        Example::

            async for message in socket:
                handle(message)
        """
        if self.websocket is None:
            raise StopAsyncIteration
        try:
            return await self.websocket.recv()
        except ConnectionClosed as exc:
            raise StopAsyncIteration from exc
