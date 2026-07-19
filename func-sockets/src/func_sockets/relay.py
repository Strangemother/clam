"""Graph-room routing for the standalone WebSocket relay.

Use this module when you need to group live sockets by graph ID and forward a
message to the other sockets in that graph. It knows only about room binding;
all graph commands and events remain opaque payloads.

Minimal use::

    relay = GraphRelay()
    relay.bind(graph_socket, "graph-42")
    relay.bind(ui_socket, "graph-42")
    await relay.receive(graph_socket, '{"name":"graph.idle"}')

The final line sends the message to ``ui_socket`` but not back to
``graph_socket``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import Hashable
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit


LOG = logging.getLogger("func-sockets")


def graph_id_from_path(path: str | None) -> str | None:
    """Return the graph ID selected by a WebSocket URL.

    Use this before registering a new connection. Supported forms include
    ``/graph/demo``, ``/demo``, and ``/?graph_id=demo``.

    Example::

        graph_id = graph_id_from_path("/graph/demo")
        assert graph_id == "demo"
    """
    parsed = urlsplit(path or "")
    query_graph_id = parse_qs(parsed.query).get("graph_id", [None])[0]
    if query_graph_id:
        return unquote(query_graph_id)

    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2 and parts[0] in {"graph", "graphs"}:
        return parts[1]
    return None


class GraphRelay:
    """Keep socket-to-graph bindings and relay traffic between room peers.

    Create one instance for one relay server process. Call :meth:`bind` when a
    socket selects a graph, :meth:`receive` for each incoming message, and
    :meth:`unbind` when the socket closes.

    Example::

        relay = GraphRelay()
        relay.bind(websocket, "demo")
        await relay.receive(websocket, "hello")
    """

    def __init__(self) -> None:
        """Create an empty relay with no graph rooms or client bindings."""
        self._rooms: dict[str, set[Hashable]] = defaultdict(set)
        self._bindings: dict[Hashable, str] = {}
        self._send_locks: dict[Hashable, asyncio.Lock] = {}

    def graph_for(self, websocket: Hashable) -> str | None:
        """Return the graph currently selected by a socket, if any."""
        return self._bindings.get(websocket)

    def bind(self, websocket: Hashable, graph_id: str) -> str:
        """Bind a socket to one graph and return the normalized graph ID."""
        if not isinstance(graph_id, str):
            raise TypeError("graph_id must be a string")
        resolved_id = str(graph_id).strip()
        if not resolved_id:
            raise ValueError("graph_id must not be empty")

        self.unbind(websocket)
        self._bindings[websocket] = resolved_id
        self._rooms[resolved_id].add(websocket)
        self._send_locks.setdefault(websocket, asyncio.Lock())
        LOG.info("client bound to graph %s (%d clients)", resolved_id, len(self._rooms[resolved_id]))
        return resolved_id

    def unbind(self, websocket: Hashable) -> None:
        """Remove a socket from its graph room."""
        graph_id = self._bindings.pop(websocket, None)
        if graph_id is None:
            return

        room = self._rooms.get(graph_id)
        if room is not None:
            room.discard(websocket)
            if not room:
                self._rooms.pop(graph_id, None)
        self._send_locks.pop(websocket, None)

    async def receive(self, websocket: Any, message: str | bytes) -> None:
        """Process a bind control message or relay one application message."""
        is_bind, bind_graph_id = self._read_bind_message(message)
        if is_bind:
            try:
                graph_id = self.bind(websocket, bind_graph_id)
            except (TypeError, ValueError) as exc:
                await self._send_json(websocket, {"type": "error", "message": str(exc)})
            else:
                await self._send_json(websocket, {"type": "bound", "graph_id": graph_id})
            return

        graph_id = self.graph_for(websocket)
        if graph_id is None:
            await self._send_json(
                websocket,
                {"type": "error", "message": "bind to a graph before sending messages"},
            )
            return

        await self.broadcast(graph_id, message, exclude=websocket)

    async def broadcast(
        self,
        graph_id: str,
        message: str | bytes,
        exclude: Hashable | None = None,
    ) -> None:
        """Send a message to every live socket in one graph."""
        peers = [peer for peer in self._rooms.get(graph_id, ()) if peer is not exclude]
        if not peers:
            return

        results = await asyncio.gather(
            *(self._send(peer, message) for peer in peers),
            return_exceptions=True,
        )
        for peer, result in zip(peers, results):
            if isinstance(result, Exception):
                LOG.debug("removing failed client from graph %s: %s", graph_id, result)
                self.unbind(peer)

    async def _send(self, websocket: Any, message: str | bytes) -> None:
        """Serialize concurrent writes and send one raw socket message."""
        lock = self._send_locks.setdefault(websocket, asyncio.Lock())
        async with lock:
            await websocket.send(message)

    async def _send_json(self, websocket: Any, payload: dict[str, Any]) -> None:
        """Encode a relay control response as JSON and send it to one socket."""
        await self._send(websocket, json.dumps(payload, separators=(",", ":")))

    @staticmethod
    def _read_bind_message(message: str | bytes) -> tuple[bool, Any]:
        """Identify a relay bind message and return its requested graph ID."""
        if not isinstance(message, str):
            return False, None
        try:
            payload = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return False, None
        if not isinstance(payload, dict) or payload.get("type") != "bind":
            return False, None
        return True, payload.get("graph_id")
