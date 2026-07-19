"""Reusable Python client for a single Func Sockets graph room."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed


class GraphSocket:
    """Connect a Python producer or consumer to one graph room."""

    def __init__(self, graph_id: str, base_url: str = "ws://127.0.0.1:8777") -> None:
        """Prepare a client URL for ``graph_id`` without connecting yet."""
        self.url = f"{base_url.rstrip('/')}/graph/{quote(graph_id, safe='')}"
        self.websocket = None

    async def __aenter__(self) -> GraphSocket:
        """Open the socket and return this bound client."""
        self.websocket = await connect(self.url)
        await self.websocket.recv()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close the socket when leaving its ``async with`` block."""
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None

    async def send(self, message: str | bytes | dict[str, Any]) -> None:
        """Send text, bytes, or a JSON-serializable dictionary to graph peers."""
        if self.websocket is None:
            raise RuntimeError("GraphSocket is not connected")
        if isinstance(message, dict):
            message = json.dumps(message)
        await self.websocket.send(message)

    async def receive(self) -> str | bytes:
        """Wait for and return the next message from another graph peer."""
        if self.websocket is None:
            raise RuntimeError("GraphSocket is not connected")
        return await self.websocket.recv()

    def __aiter__(self) -> GraphSocket:
        """Return this client as an async stream of incoming messages."""
        return self

    async def __anext__(self) -> str | bytes:
        """Return the next message, ending iteration after socket closure."""
        if self.websocket is None:
            raise StopAsyncIteration
        try:
            return await self.websocket.recv()
        except ConnectionClosed as exc:
            raise StopAsyncIteration from exc
