"""
ws_server.py
──────────────────────────────────────────────────────────────────────────────
WebSocket transport for GraphRunner.

Clients connect and can:

  • Send commands (same dict protocol as runner.send)
  • Receive live telemetry pushed after every N ticks (push_interval)
  • Receive a reply for 'read' / 'read_all' requests

Wire format: newline-delimited JSON over a single WebSocket connection.

Message types (server → client)
─────────────────────────────────
  { "type": "tick",  "panels": [ ... ] }         — periodic push
  { "type": "reply", "panels": [ ... ] }          — response to read_all
  { "type": "reply", "panel":  { ... } }          — response to read
  { "type": "error", "message": "..." }           — command error

Message types (client → server)
─────────────────────────────────
Any valid GraphRunner command dict.  'reply' field is ignored/injected by the
server.  Example:

  {"op":"set",  "id":3, "key":"enabled", "value":false}
  {"op":"toggle","id":3}
  {"op":"read", "id":16}
  {"op":"read_all"}

Usage
─────
  from power_graph.runner import GraphRunner
  from power_graph.ws_server import GraphWSServer

  runner = GraphRunner('spaceship.json', fps=20)
  server = GraphWSServer(runner, host='localhost', port=8765, push_interval=4)

  asyncio.run(asyncio.gather(
      runner.run(),
      server.serve(),
  ))

Dependency: websockets>=12  (pip install power-graph[server])
"""

import asyncio
import json
import logging
from typing import Set

log = logging.getLogger(__name__)


class GraphWSServer:
    """
    WebSocket server that bridges browser/external clients to a GraphRunner.

    push_interval: push full panel state to all clients every N ticks.
                   0 disables automatic push (clients must poll with read_all).
    """

    def __init__(self, runner, host: str = 'localhost', port: int = 8765,
                 push_interval: int = 4):
        """
        Args:
            runner:        GraphRunner instance (must already be configured).
            host:          Bind address.
            port:          Bind port.
            push_interval: Push state to all clients every N ticks (>0).
                           At fps=20 and push_interval=4 → 5 Hz push.
        """
        self._runner        = runner
        self._host          = host
        self._port          = port
        self._push_interval = push_interval
        self._clients: Set  = set()
        self._tick_count    = 0

        if push_interval > 0:
            runner.subscribe(self._on_tick)

    # ── Public ────────────────────────────────────────────────────────────────

    async def serve(self) -> None:
        """Start the WebSocket server.  Runs until cancelled."""
        try:
            import websockets
        except ImportError as exc:
            raise ImportError(
                "websockets is required for GraphWSServer.  "
                "Install it with:  pip install 'power-graph[server]'"
            ) from exc

        log.info("GraphWSServer: listening on ws://%s:%d", self._host, self._port)
        async with websockets.serve(self._handle, self._host, self._port):
            await asyncio.Future()   # run forever

    # ── WebSocket handler ─────────────────────────────────────────────────────

    async def _handle(self, websocket) -> None:
        self._clients.add(websocket)
        log.debug("GraphWSServer: client connected (%d total)", len(self._clients))
        try:
            async for raw in websocket:
                await self._dispatch(websocket, raw)
        except Exception as exc:
            log.debug("GraphWSServer: client disconnected — %s", exc)
        finally:
            self._clients.discard(websocket)
            log.debug("GraphWSServer: client removed (%d remaining)", len(self._clients))

    async def _dispatch(self, websocket, raw: str) -> None:
        try:
            cmd = json.loads(raw)
        except json.JSONDecodeError as exc:
            await self._send(websocket, {'type': 'error', 'message': f'invalid JSON: {exc}'})
            return

        op = cmd.get('op')

        if op in ('read', 'read_all', 'read_connections'):
            # Inject a Future so we can await the result and send it back.
            loop  = asyncio.get_event_loop()
            reply = loop.create_future()
            cmd['reply'] = reply
            self._runner.send(cmd)
            try:
                result = await asyncio.wait_for(reply, timeout=2.0)
            except asyncio.TimeoutError:
                await self._send(websocket, {'type': 'error', 'message': 'read timed out'})
                return

            if op == 'read_all':
                await self._send(websocket, {'type': 'reply', 'panels': result})
            elif op == 'read_connections':
                await self._send(websocket, {'type': 'reply', 'connections': result})
            else:
                await self._send(websocket, {'type': 'reply', 'panel': result})
        else:
            # Fire-and-forget mutation — remove 'reply' if client accidentally sent one.
            cmd.pop('reply', None)
            self._runner.send(cmd)

    # ── Tick subscriber ───────────────────────────────────────────────────────

    def _on_tick(self, panels) -> None:
        """Called by GraphRunner after every tick (sync context)."""
        self._tick_count += 1
        if self._push_interval > 0 and self._tick_count % self._push_interval == 0:
            # Schedule the async broadcast without blocking the tick.
            asyncio.get_event_loop().call_soon(
                lambda: asyncio.ensure_future(self._broadcast_state(panels))
            )

    async def _broadcast_state(self, panels) -> None:
        if not self._clients:
            return
        message = json.dumps({'type': 'tick', 'panels': [dict(p) for p in panels]})
        dead = set()
        for ws in self._clients:
            try:
                await ws.send(message)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    async def _send(websocket, data: dict) -> None:
        try:
            await websocket.send(json.dumps(data))
        except Exception as exc:
            log.debug("GraphWSServer: send failed — %s", exc)
