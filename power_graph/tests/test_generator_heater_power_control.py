"""
test_generator_heater_power_control.py
──────────────────────────────────────────────────────────────────────────────
Regression tests: generator on/off and enable/disable must propagate correctly
to a connected heater.

Background
──────────
powerSources is a dict keyed by source panel ID.  When a layout is saved and
reloaded, JSON turns all keys to strings (e.g. {3: {...}} → {"3": {...}}).
A bug caused receive() to look up the source using an int key while the stored
entry was a str key, so the stale signal was never cleared when the generator
turned off.  The heater remained in 'on' state indefinitely.

These tests exercise:
  1. Generator toggle off  → heater goes off
  2. Generator toggle on   → heater returns to on
  3. Generator enabled=False + repropagate → heater goes off
  4. Generator enabled=True  + repropagate → heater returns to on
  5. The same 4 cases after loading from a saved layout JSON (str-key
     powerSources) — this is the exact regression scenario.

Run:
    cd power_graph && python -m pytest tests/test_generator_heater_power_control.py -v
"""

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

import power_graph.nodes  # noqa — registers all node types as side-effect
from power_graph.graph import PowerGraph
from power_graph.loader import load_layout
from power_graph.node_registry import NodeRegistry


# ── Helpers ───────────────────────────────────────────────────────────────────

HEATER_PRESET = {
    'watts':       1000,
    'minWatts':    50,
    'heatRate':    0.1,   # slow — thermal behaviour not the focus here
    'coolRate':    0.1,
    'maxTemp':     80.0,
    'resetTemp':   60.0,
    'noise':       0,
}


def _build():
    """
    Return (graph, gen, heater) — live generator wired to heater.
    Built entirely through the Python API (no JSON involved).
    """
    graph = PowerGraph()
    gen   = graph.spawn('gen',    label='Gen',    preset={'volts': 240, 'amps': 20})
    heater = graph.spawn('heater', label='Heater', preset=HEATER_PRESET)

    gen['live'] = True
    graph.connect(gen, 0, heater, 0)
    graph.repropagate_all()
    graph.update_all_gen_draws()
    return graph, gen, heater


def _tick(graph, steps=5, fps=20):
    dt = 1.0 / fps
    for _ in range(steps):
        for panel in graph.panels:
            cls = NodeRegistry.get(panel['type'])
            if cls:
                cls.tick(panel, dt, graph)
        graph.update_all_gen_draws()


def _layout_json(gen_id: int, heater_id: int) -> dict:
    """
    Build a minimal layout dict that mimics what JSON round-trip produces:
    - powerSources keys are *strings* (this is the regression scenario)
    - signal carries a stale live reading
    """
    return {
        "nodes": [
            {
                "id": gen_id,
                "type": "gen",
                "title": "Gen",
                "config": {
                    "label": "Gen",
                    "enabled": True,
                    "volts": 240,
                    "amps": 20,
                    "live": True,
                    "state": "on",
                },
            },
            {
                "id": heater_id,
                "type": "heater",
                "title": "Heater",
                "config": {
                    **HEATER_PRESET,
                    "label": "Heater",
                    "enabled": True,
                    # Stale JSON-serialised powerSources — keys are strings
                    "powerSources": {str(gen_id): {"v": 240, "a": 20}},
                    "signal": {"v": 240, "a": 20},
                    "state": "on",
                    "current_watts": 50,
                },
            },
        ],
        "connections": [
            {
                "sender":   {"label": gen_id,    "direction": "outbound", "pipIndex": 0},
                "receiver": {"label": heater_id, "direction": "inbound",  "pipIndex": 0},
            }
        ],
        "edges": {},
    }


def _build_from_layout():
    """Return (graph, gen, heater) loaded via load_layout (the JSON path)."""
    graph = PowerGraph()
    layout = _layout_json(gen_id=1, heater_id=2)
    load_layout(graph, layout)
    graph.update_all_gen_draws()
    gen    = next(p for p in graph.panels if p['type'] == 'gen')
    heater = next(p for p in graph.panels if p['type'] == 'heater')
    return graph, gen, heater


# ── Tests: Python API (no JSON round-trip) ────────────────────────────────────

class TestGeneratorToggle:
    """Generator toggle must propagate to heater via Python API."""

    def test_heater_on_when_generator_live(self):
        _, gen, heater = _build()
        assert heater['state'] in ('on', 'brownout'), \
            f"Expected heater on, got {heater['state']!r}"

    def test_heater_off_when_generator_toggled_off(self):
        graph, gen, heater = _build()
        NodeRegistry.get('gen').toggle(gen, graph)    # live → False
        _tick(graph)
        assert heater['state'] == 'off', \
            f"Heater should be off after gen toggle, got {heater['state']!r}"

    def test_heater_on_again_after_generator_toggled_back_on(self):
        graph, gen, heater = _build()
        NodeRegistry.get('gen').toggle(gen, graph)    # off
        _tick(graph)
        NodeRegistry.get('gen').toggle(gen, graph)    # on again
        _tick(graph)
        assert heater['state'] in ('on', 'brownout'), \
            f"Heater should be on after gen re-enable, got {heater['state']!r}"


class TestGeneratorEnabled:
    """Generator enabled=False must propagate to heater via Python API."""

    def test_heater_off_when_generator_disabled(self):
        graph, gen, heater = _build()
        gen['enabled'] = False
        graph.repropagate_all()
        _tick(graph)
        assert heater['state'] == 'off', \
            f"Heater should be off when gen disabled, got {heater['state']!r}"

    def test_heater_on_when_generator_re_enabled(self):
        graph, gen, heater = _build()
        gen['enabled'] = False
        graph.repropagate_all()
        _tick(graph)
        gen['enabled'] = True
        graph.repropagate_all()
        _tick(graph)
        assert heater['state'] in ('on', 'brownout'), \
            f"Heater should be on after gen re-enabled, got {heater['state']!r}"


# ── Tests: JSON round-trip (str-key powerSources regression) ──────────────────

class TestGeneratorToggleAfterLayoutLoad:
    """Same toggle tests but graph is loaded via load_layout (JSON path)."""

    def test_heater_on_when_generator_live(self):
        _, gen, heater = _build_from_layout()
        assert heater['state'] in ('on', 'brownout'), \
            f"Expected heater on after layout load, got {heater['state']!r}"

    def test_heater_off_when_generator_toggled_off(self):
        graph, gen, heater = _build_from_layout()
        NodeRegistry.get('gen').toggle(gen, graph)    # live → False
        _tick(graph)
        assert heater['state'] == 'off', (
            f"Heater should be off after gen toggle on JSON-loaded graph, "
            f"got {heater['state']!r}. powerSources={heater.get('powerSources')}"
        )

    def test_heater_on_again_after_generator_toggled_back_on(self):
        graph, gen, heater = _build_from_layout()
        NodeRegistry.get('gen').toggle(gen, graph)
        _tick(graph)
        NodeRegistry.get('gen').toggle(gen, graph)
        _tick(graph)
        assert heater['state'] in ('on', 'brownout'), \
            f"Heater should be on after gen re-enable, got {heater['state']!r}"

    def test_powersources_cleared_on_load(self):
        """
        load_layout must wipe stale powerSources so the first propagation
        rewrites them via receive().
        """
        graph, gen, heater = _build_from_layout()
        # After load_layout + repropagate, all powerSources entries must have
        # been written by live receive() calls, not carried over from JSON.
        for src_val in heater.get('powerSources', {}).values():
            assert isinstance(src_val, dict) and 'v' in src_val, \
                "powerSources entry must be a {v, a} signal dict"


class TestGeneratorEnabledAfterLayoutLoad:
    """Generator enabled=False must propagate after JSON load."""

    def test_heater_off_when_generator_disabled(self):
        graph, gen, heater = _build_from_layout()
        gen['enabled'] = False
        graph.repropagate_all()
        _tick(graph)
        assert heater['state'] == 'off', (
            f"Heater should be off when gen disabled on JSON-loaded graph, "
            f"got {heater['state']!r}. powerSources={heater.get('powerSources')}"
        )

    def test_heater_on_when_generator_re_enabled(self):
        graph, gen, heater = _build_from_layout()
        gen['enabled'] = False
        graph.repropagate_all()
        _tick(graph)
        gen['enabled'] = True
        graph.repropagate_all()
        _tick(graph)
        assert heater['state'] in ('on', 'brownout'), \
            f"Heater should be on after gen re-enabled, got {heater['state']!r}"
