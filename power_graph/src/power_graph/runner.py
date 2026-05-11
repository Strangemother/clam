"""
runner.py
──────────────────────────────────────────────────────────────────────────────
GraphRunner — async loop with an injectable command queue.

The runner owns a PowerGraph and advances it at a fixed FPS.  External code
(WebSocket handlers, HTTP endpoints, tests, coroutines) submits commands via
runner.send() without knowing anything about the loop internals.

Command protocol
───────────────
Every command is a plain dict with an 'op' key:

  set        Write a single field on a panel.
             { 'op': 'set', 'id': 3, 'key': 'enabled', 'value': False }

  toggle     Call the node class's toggle() method (gen on/off, breaker, etc.)
             { 'op': 'toggle', 'id': 3 }

  reset      Call the node class's reset() method on a single panel.
             { 'op': 'reset', 'id': 16 }

  connect    Wire two panels together and repropagate.
             { 'op': 'connect',
               'from_id': 1, 'from_pip': 0,
               'to_id': 5,   'to_pip': 0,
               'wire': {'wireType': 'copper', 'length': 1} }

  disconnect Remove a connection by key and repropagate.
             { 'op': 'disconnect', 'conn_key': '1:0->5:0' }

  spawn      Add a new panel at runtime.
             { 'op': 'spawn', 'node_type': 'load',
               'label': 'New Load', 'preset': {'watts': 500} }

  remove     Remove a panel and all its connections.
             { 'op': 'remove', 'id': 42 }

  repropagate  Force a full repropagate_all() on the next tick boundary.
             { 'op': 'repropagate' }

  read       Return a snapshot of one panel via an asyncio.Future.
             { 'op': 'read', 'id': 16, 'reply': <asyncio.Future> }

  read_all   Return snapshots of all panels via an asyncio.Future.
             { 'op': 'read_all', 'reply': <asyncio.Future> }

Reading values
─────────────
  loop = asyncio.get_event_loop()
  reply = loop.create_future()
  runner.send({'op': 'read', 'id': 16, 'reply': reply})
  snapshot = await reply          # dict copy of the panel state

Sending from a different OS thread
───────────────────────────────────
  loop.call_soon_threadsafe(runner.send, command)

Usage
─────
  runner = GraphRunner('spaceship.json', fps=20)
  await runner.run()               # blocks — launch with asyncio.create_task()

  # Or drive manually in tests:
  runner = GraphRunner('spaceship.json', fps=20)
  runner.tick_once()               # synchronous single tick, no asyncio needed
"""

import asyncio
import time
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .graph import PowerGraph
from .loader import load_layout_file
from .node_registry import NodeRegistry

log = logging.getLogger(__name__)


class GraphRunner:
    """
    Drives a PowerGraph at a fixed frame rate using an asyncio event loop.

    All mutation from outside the loop goes through runner.send(command).
    Commands are drained and applied at the *start* of each tick so the graph
    is never mutated mid-calculation.
    """

    def __init__(self, layout_path: str | Path, fps: int = 20):
        """
        Args:
            layout_path: Path to a layout JSON file (loaded immediately).
            fps:         Target tick rate.  The loop sleeps the remainder of
                         each 1/fps window after ticking.
        """
        self.fps      = fps
        self._dt      = 1.0 / fps
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

        # Subscribers: called after every tick with the full panels list.
        # Signature: callback(panels: list[dict]) -> None
        self._tick_subscribers: List[Callable] = []

        self.graph = PowerGraph()
        load_layout_file(self.graph, layout_path)
        log.debug("GraphRunner: loaded layout %s", layout_path)

    # ── Public API ────────────────────────────────────────────────────────────

    def send(self, command: Dict[str, Any]) -> None:
        """
        Inject a command into the queue.

        Thread-safe as long as you call this from within the same event loop,
        or use loop.call_soon_threadsafe(runner.send, cmd) from other threads.
        """
        self._queue.put_nowait(command)

    def subscribe(self, callback: Callable[[List[Dict]], None]) -> None:
        """
        Register a callback invoked after each tick with the current panels.

        Useful for broadcast: the WebSocket server registers a subscriber that
        fans out state to all connected clients.
        """
        self._tick_subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        self._tick_subscribers = [s for s in self._tick_subscribers if s is not callback]

    def tick_once(self, dt: float = None) -> None:
        """
        Advance the simulation by one tick synchronously (no asyncio needed).

        Useful in tests and for embedding the runner in an external game loop.
        """
        self._drain_queue()
        self._tick(dt or self._dt)
        self._notify_subscribers()

    async def stop(self) -> None:
        """Signal the run loop to exit after the current tick."""
        self._running = False

    # ── Async loop ────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """
        Run the simulation loop until stop() is called.

        Launch as a coroutine alongside other tasks:
            asyncio.gather(runner.run(), ws_server.serve(...))
        """
        self._running = True
        log.info("GraphRunner: starting at %d fps", self.fps)

        while self._running:
            tick_start = time.monotonic()
            self._drain_queue()
            self._tick(self._dt)
            self._notify_subscribers()
            elapsed = time.monotonic() - tick_start
            sleep_s = max(0.0, self._dt - elapsed)
            await asyncio.sleep(sleep_s)

        log.info("GraphRunner: stopped")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _drain_queue(self) -> None:
        """Apply all pending commands before this tick fires."""
        while not self._queue.empty():
            cmd = self._queue.get_nowait()
            try:
                self._apply(cmd)
            except Exception as exc:
                log.warning("GraphRunner: error applying command %s — %s", cmd, exc)

    def _tick(self, dt: float) -> None:
        for panel in self.graph.panels:
            node_cls = NodeRegistry.get(panel['type'])
            if node_cls:
                node_cls.tick(panel, dt, self.graph)
        self.graph.update_all_gen_draws()

    def _notify_subscribers(self) -> None:
        if not self._tick_subscribers:
            return
        # Pass a shallow list of panel dicts — subscribers must not mutate;
        # mutations must come through send().
        panels = self.graph.panels
        for cb in self._tick_subscribers:
            try:
                cb(panels)
            except Exception as exc:
                log.warning("GraphRunner: subscriber error — %s", exc)

    def _apply(self, cmd: Dict[str, Any]) -> None:
        op = cmd.get('op')

        # ── Helpers ───────────────────────────────────────────────────────────

        def panel(required=True):
            p = self.graph._find_panel(cmd['id'])
            if p is None and required:
                raise KeyError(f"panel id={cmd['id']} not found")
            return p

        def resolve(future, value):
            if future and not future.done():
                future.set_result(value)

        # ── Operations ────────────────────────────────────────────────────────

        if op == 'set':
            p = panel()
            p[cmd['key']] = cmd['value']

        elif op == 'toggle':
            p = panel()
            node_cls = NodeRegistry.get(p['type'])
            if hasattr(node_cls, 'toggle'):
                node_cls.toggle(p, self.graph)
            else:
                # Generic toggle: flip enabled and repropagate so graph.py's
                # enabled-check in _propagate() handles the off/on transition.
                p['enabled'] = not p.get('enabled', True)
                self.graph.repropagate_all()

        elif op == 'reset':
            p = panel()
            node_cls = NodeRegistry.get(p['type'])
            if node_cls:
                node_cls.reset(p, self.graph)

        elif op == 'connect':
            from_panel = self.graph._find_panel(cmd['from_id'])
            to_panel   = self.graph._find_panel(cmd['to_id'])
            if from_panel is None:
                raise KeyError(f"connect: from_id={cmd['from_id']} not found")
            if to_panel is None:
                raise KeyError(f"connect: to_id={cmd['to_id']} not found")
            self.graph.connect(
                from_panel, cmd.get('from_pip', 0),
                to_panel,   cmd.get('to_pip', 0),
                **(cmd.get('wire') or {}),
            )
            self.graph.repropagate_all()

        elif op == 'disconnect':
            removed = self.graph.disconnect(cmd['conn_key'])
            if removed:
                self.graph.repropagate_all()

        elif op == 'spawn':
            self.graph.spawn(
                cmd['node_type'],
                label=cmd.get('label'),
                preset=cmd.get('preset'),
            )

        elif op == 'remove':
            self.graph.remove_panel(cmd['id'])
            self.graph.repropagate_all()

        elif op == 'repropagate':
            self.graph.repropagate_all()

        elif op == 'read':
            p = panel()
            resolve(cmd.get('reply'), dict(p))

        elif op == 'read_all':
            resolve(cmd.get('reply'), [dict(p) for p in self.graph.panels])

        elif op == 'read_connections':
            edges = []
            for (from_id, from_pip), targets in self.graph._connections.items():
                for to_id, to_pip, conn_key in targets:
                    edges.append({
                        'from_id':  from_id,
                        'from_pip': from_pip,
                        'to_id':    to_id,
                        'to_pip':   to_pip,
                        'key':      conn_key,
                    })
            resolve(cmd.get('reply'), edges)

        else:
            raise ValueError(f"unknown op: {op!r}")
