"""
test_ws_broadcast_serialisation.py
──────────────────────────────────────────────────────────────────────────────
Regression tests: _broadcast_state must not raise TypeError when a panel dict
contains nested dicts with mixed int and str keys.

Background
──────────
json.dumps(..., sort_keys=True) requires all sibling keys within a nested dict
to be mutually comparable.  When a panel dict contains something like

    powerSources: {3: {...}}   ← int key (runtime)
    powerSources: {"3": {...}} ← str key (after JSON round-trip)

or any other nested dict mixing key types, sort_keys=True raises:

    TypeError: '<' not supported between instances of 'int' and 'str'

The fix was to drop sort_keys=True.  These tests confirm:
  1. A panel with int-keyed nested dicts serialises without error.
  2. A panel with str-keyed nested dicts serialises without error.
  3. A panel with *mixed* int+str sibling keys in the same nested dict
     serialises without error (the pathological case).
  4. The snapshot diff logic still correctly detects changed vs unchanged
     panels without sort_keys (insertion-order is stable in Python 3.7+).
  5. _broadcast_state produces a valid JSON 'tick' message containing
     every changed panel.

Run:
    cd power_graph && python -m pytest tests/test_ws_broadcast_serialisation.py -v
"""

import asyncio
import json
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

import power_graph.nodes  # noqa
from power_graph.ws_server import GraphWSServer


# ── Minimal runner stub ───────────────────────────────────────────────────────

class _FakeRunner:
    """Minimal stub — GraphWSServer only needs subscribe() at __init__."""
    def subscribe(self, cb): pass
    def send(self, cmd):     pass


def _make_server():
    return GraphWSServer(_FakeRunner(), push_interval=1)


# ── Panel factory helpers ─────────────────────────────────────────────────────

def _panel_int_keys():
    """Panel whose powerSources has int keys (runtime-built graph)."""
    return {
        'id':           1,
        'type':         'gen',
        'label':        'Gen',
        'state':        'on',
        'powerSources': {1: {'v': 240, 'a': 10}, 2: {'v': 240, 'a': 5}},
    }


def _panel_str_keys():
    """Panel whose powerSources has str keys (JSON-loaded graph)."""
    return {
        'id':           2,
        'type':         'heater',
        'label':        'Heater',
        'state':        'on',
        'powerSources': {'1': {'v': 240, 'a': 10}},
    }


def _panel_mixed_keys():
    """
    Panel with a nested dict containing BOTH int and str sibling keys —
    the exact scenario that caused sort_keys=True to raise TypeError.
    """
    return {
        'id':           3,
        'type':         'load',
        'label':        'Mixed',
        'state':        'on',
        'powerSources': {1: {'v': 240, 'a': 10}, '2': {'v': 120, 'a': 5}},
    }


# ── Serialisation unit tests ──────────────────────────────────────────────────

class TestPanelSerialisation:
    """json.dumps of a panel copy must never raise TypeError."""

    def _serialise(self, panel):
        """Mirror exactly what _broadcast_state does."""
        panel_copy = dict(panel)
        return json.dumps(panel_copy)   # no sort_keys

    def test_int_keys_no_error(self):
        self._serialise(_panel_int_keys())

    def test_str_keys_no_error(self):
        self._serialise(_panel_str_keys())

    def test_mixed_keys_no_error(self):
        """This was the bug — must not raise TypeError."""
        self._serialise(_panel_mixed_keys())

    def test_output_is_valid_json(self):
        for panel in [_panel_int_keys(), _panel_str_keys(), _panel_mixed_keys()]:
            raw = self._serialise(panel)
            parsed = json.loads(raw)
            assert isinstance(parsed, dict)


# ── Snapshot diff tests ───────────────────────────────────────────────────────

class TestSnapshotDiff:
    """
    _broadcast_state uses a snapshot string to skip unchanged panels.
    Without sort_keys the comparison must still be stable across multiple
    calls with identical data.
    """

    def _direct_snapshots(self, server, panels):
        """
        Exercise the snapshot logic directly without needing live WebSocket
        clients — replicate the loop from _broadcast_state.
        """
        changed = []
        for p in panels:
            pid = p['id']
            panel_copy = dict(p)
            panel_json = json.dumps(panel_copy)
            if server._panel_snapshots.get(pid) != panel_json:
                changed.append(panel_copy)
                server._panel_snapshots[pid] = panel_json
        return changed

    def test_first_call_marks_all_changed(self):
        server = _make_server()
        panels = [_panel_int_keys(), _panel_str_keys()]
        changed = self._direct_snapshots(server, panels)
        assert len(changed) == 2

    def test_second_call_with_same_data_marks_nothing_changed(self):
        server = _make_server()
        panels = [_panel_int_keys(), _panel_str_keys()]
        self._direct_snapshots(server, panels)           # populate snapshots
        changed = self._direct_snapshots(server, panels) # same data
        assert changed == [], f"Expected no changes, got {changed}"

    def test_mutated_panel_detected_as_changed(self):
        server = _make_server()
        panel  = _panel_str_keys()
        self._direct_snapshots(server, [panel])

        # Mutate a field
        panel['state'] = 'off'
        changed = self._direct_snapshots(server, [panel])
        assert len(changed) == 1
        assert changed[0]['state'] == 'off'

    def test_mixed_key_panel_stable_across_calls(self):
        """The pathological panel must produce a stable snapshot string."""
        server = _make_server()
        panel  = _panel_mixed_keys()
        self._direct_snapshots(server, [panel])
        changed = self._direct_snapshots(server, [panel])
        assert changed == [], "Mixed-key panel snapshot must be stable"


# ── _broadcast_state integration (no real WebSocket) ─────────────────────────

class TestBroadcastState:
    """
    _broadcast_state with a fake client — verifies the tick message is well-
    formed and contains the expected panels, without needing a real WebSocket.
    """

    @pytest.mark.asyncio
    async def test_sends_tick_message_to_client(self):
        server   = _make_server()
        received = []

        class _FakeWS:
            async def send(self, msg):
                received.append(msg)

        server._clients.add(_FakeWS())
        await server._broadcast_state([_panel_int_keys(), _panel_str_keys()])

        assert len(received) == 1
        msg = json.loads(received[0])
        assert msg['type'] == 'tick'
        assert len(msg['panels']) == 2

    @pytest.mark.asyncio
    async def test_no_message_when_panels_unchanged(self):
        server = _make_server()
        received = []

        class _FakeWS:
            async def send(self, msg):
                received.append(msg)

        ws = _FakeWS()
        server._clients.add(ws)

        panels = [_panel_str_keys()]
        await server._broadcast_state(panels)   # first call — sends
        await server._broadcast_state(panels)   # second call — unchanged

        assert len(received) == 1, \
            "Should only send once; second call had no changes"

    @pytest.mark.asyncio
    async def test_mixed_key_panel_no_error(self):
        """
        Regression: _broadcast_state with a mixed-key panel must not raise
        TypeError (the sort_keys=True bug).
        """
        server = _make_server()

        class _FakeWS:
            async def send(self, msg): pass

        server._clients.add(_FakeWS())
        # Must not raise
        await server._broadcast_state([_panel_mixed_keys()])

    @pytest.mark.asyncio
    async def test_dead_client_removed(self):
        server = _make_server()

        class _DeadWS:
            async def send(self, msg):
                raise ConnectionError("gone")

        server._clients.add(_DeadWS())
        await server._broadcast_state([_panel_str_keys()])
        assert len(server._clients) == 0, "Dead client should be removed"
