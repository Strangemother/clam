"""
test_runner.py
──────────────────────────────────────────────────────────────────────────────
Integration tests for GraphRunner — the async command-queue loop.

Tests use tick_once() (synchronous) to drive the runner without asyncio,
plus a short asyncio.run() test to confirm the async loop also works.

Coverage:
  • tick_once() — drives the graph without asyncio
  • send() / 'set'     — mutate a panel field
  • send() / 'toggle'  — call node toggle()
  • send() / 'reset'   — call node reset()
  • send() / 'read'    — return a snapshot via Future (async)
  • send() / 'read_all' — return all panels via Future (async)
  • send() / 'repropagate' — force propagation
  • subscribe() / unsubscribe() — tick notification callbacks
  • Commands are applied *before* the tick they arrive in
  • Bad commands raise inside _apply, not in send()
  • async run() loop — starts, ticks, stops cleanly
"""

import asyncio
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from power_graph import GraphRunner

LAYOUT = pathlib.Path(__file__).parent.parent.parent / 'func-pipes' / 'layouts' / 'spaceship.json'


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_runner() -> GraphRunner:
    """Fresh runner with generators offline (safe-start state)."""
    import json
    from power_graph.loader import load_layout
    from power_graph import PowerGraph
    from power_graph.nodes.generator import Generator

    layout = json.load(open(LAYOUT))
    for node in layout['nodes']:
        if node.get('type') == 'gen':
            node.setdefault('config', {})['live'] = False

    runner = GraphRunner.__new__(GraphRunner)
    runner.fps = 20
    runner._dt = 1.0 / 20
    runner._queue = asyncio.Queue()
    runner._running = False
    runner._tick_subscribers = []
    runner.graph = PowerGraph()
    load_layout(runner.graph, layout)
    return runner


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSyncTick:
    """tick_once() exercises without asyncio."""

    def test_tick_once_advances_simulation(self):
        """Calling tick_once() runs one dt without raising."""
        runner = make_runner()
        # No generators live — panels should all be idle, no crash
        runner.tick_once()
        runner.tick_once()
        # Nothing blown because gens are offline
        blown = [p for p in runner.graph.panels if p.get('state') == 'blown']
        assert len(blown) == 0

    def test_set_command_applied_before_tick(self):
        """'set' command takes effect at the start of the tick in which it's queued."""
        runner = make_runner()
        gen3 = runner.graph._find_panel(3)
        assert gen3 is not None

        # Queue a field write, then tick — must be applied before tick fires
        runner.send({'op': 'set', 'id': 3, 'key': 'enabled', 'value': False})
        runner.tick_once()
        assert gen3['enabled'] is False

    def test_multiple_commands_drained_in_order(self):
        """All queued commands are applied in FIFO order before the tick."""
        runner = make_runner()
        gen3 = runner.graph._find_panel(3)

        runner.send({'op': 'set', 'id': 3, 'key': '_test_marker', 'value': 1})
        runner.send({'op': 'set', 'id': 3, 'key': '_test_marker', 'value': 2})
        runner.send({'op': 'set', 'id': 3, 'key': '_test_marker', 'value': 3})
        runner.tick_once()

        assert gen3['_test_marker'] == 3

    def test_toggle_generator(self):
        """'toggle' starts a generator that was offline."""
        runner = make_runner()
        gen4 = runner.graph._find_panel(4)
        assert gen4.get('live') is False or gen4.get('state') != 'on'

        runner.send({'op': 'toggle', 'id': 4})
        runner.tick_once()

        assert gen4.get('live') is True

    def test_reset_panel(self):
        """'reset' returns a blown panel to off/unfused state."""
        runner = make_runner()
        # Manually blow a load
        load = next(p for p in runner.graph.panels if p['type'] == 'load')
        load['state'] = 'blown'
        load['blown'] = True

        runner.send({'op': 'reset', 'id': load['id']})
        runner.tick_once()

        assert load['state'] != 'blown'
        assert load.get('blown') is False

    def test_bad_op_does_not_crash_loop(self):
        """An unknown op is logged and swallowed — the loop keeps running."""
        runner = make_runner()
        runner.send({'op': 'does_not_exist', 'id': 3})
        # tick_once should not raise
        runner.tick_once()

    def test_bad_id_does_not_crash_loop(self):
        """A command with a nonexistent panel id is swallowed."""
        runner = make_runner()
        runner.send({'op': 'set', 'id': 9999, 'key': 'enabled', 'value': False})
        runner.tick_once()   # must not raise


class TestSubscribers:
    """subscribe() / unsubscribe() callback notifications."""

    def test_subscriber_called_each_tick(self):
        runner = make_runner()
        calls = []
        runner.subscribe(lambda panels: calls.append(len(panels)))

        runner.tick_once()
        runner.tick_once()
        runner.tick_once()

        assert len(calls) == 3
        assert all(n > 0 for n in calls)

    def test_unsubscribe_stops_notifications(self):
        runner = make_runner()
        calls = []

        def cb(panels):
            calls.append(1)

        runner.subscribe(cb)
        runner.tick_once()
        runner.unsubscribe(cb)
        runner.tick_once()
        runner.tick_once()

        assert len(calls) == 1

    def test_subscriber_error_does_not_crash_loop(self):
        runner = make_runner()

        def bad_cb(panels):
            raise RuntimeError("subscriber exploded")

        runner.subscribe(bad_cb)
        # Must not propagate the exception
        runner.tick_once()


class TestRepropagate:
    """'repropagate' command forces propagation."""

    def test_repropagate_command(self):
        runner = make_runner()
        # Toggle gen4 on, tick to settle, then queue a repropagate
        runner.send({'op': 'toggle', 'id': 4})
        for _ in range(20):          # 1 second
            runner.tick_once()

        runner.send({'op': 'repropagate'})
        runner.tick_once()   # must not raise

        gen4 = runner.graph._find_panel(4)
        assert gen4.get('state') == 'on'


class TestAsyncRead:
    """'read' and 'read_all' via asyncio Future."""

    @pytest.mark.asyncio
    async def test_read_single_panel(self):
        runner = make_runner()
        loop  = asyncio.get_event_loop()
        reply = loop.create_future()

        runner.send({'op': 'read', 'id': 16, 'reply': reply})
        runner.tick_once()   # drains queue → sets future result

        snapshot = await asyncio.wait_for(reply, timeout=1.0)
        assert isinstance(snapshot, dict)
        assert snapshot['id'] == 16
        assert snapshot['type'] == 'heater'

    @pytest.mark.asyncio
    async def test_read_all_panels(self):
        runner = make_runner()
        loop  = asyncio.get_event_loop()
        reply = loop.create_future()

        runner.send({'op': 'read_all', 'reply': reply})
        runner.tick_once()

        all_panels = await asyncio.wait_for(reply, timeout=1.0)
        assert isinstance(all_panels, list)
        assert len(all_panels) == len(runner.graph.panels)
        # Each entry is an independent copy
        assert all_panels[0] is not runner.graph.panels[0]

    @pytest.mark.asyncio
    async def test_read_returns_snapshot_not_live_ref(self):
        """The snapshot dict is a copy — mutating it does not affect the graph."""
        runner = make_runner()
        loop  = asyncio.get_event_loop()
        reply = loop.create_future()

        runner.send({'op': 'read', 'id': 3, 'reply': reply})
        runner.tick_once()

        snapshot = await asyncio.wait_for(reply, timeout=1.0)
        snapshot['label'] = 'mutated by test'

        live = runner.graph._find_panel(3)
        assert live['label'] != 'mutated by test'


class TestAsyncLoop:
    """Async run() loop starts, ticks, and stops cleanly."""

    @pytest.mark.asyncio
    async def test_run_and_stop(self):
        runner = make_runner()
        ticks_seen = []
        runner.subscribe(lambda panels: ticks_seen.append(1))

        task = asyncio.create_task(runner.run())

        # Let it run for ~10 ticks (0.5s at 20fps)
        await asyncio.sleep(0.5)
        await runner.stop()
        await asyncio.wait_for(task, timeout=1.0)

        # Should have fired roughly 10 ticks (allow wide tolerance for CI timing)
        assert len(ticks_seen) >= 5, f"expected >= 5 ticks, got {len(ticks_seen)}"
        assert not runner._running

    @pytest.mark.asyncio
    async def test_command_injected_into_running_loop(self):
        """send() during a live run() is picked up by the loop."""
        runner = make_runner()
        task = asyncio.create_task(runner.run())

        # Give loop a few ticks to start
        await asyncio.sleep(0.1)

        gen4 = runner.graph._find_panel(4)
        assert gen4.get('live') is not True

        runner.send({'op': 'toggle', 'id': 4})

        # Wait for the command to be processed
        await asyncio.sleep(0.2)

        assert gen4.get('live') is True, "toggle command should have been applied by the loop"

        await runner.stop()
        await asyncio.wait_for(task, timeout=1.0)


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', __file__, '-v', '-s'],
        cwd=str(pathlib.Path(__file__).parent.parent),
    )
    sys.exit(result.returncode)
