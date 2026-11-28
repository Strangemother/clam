"""
test_enabled_guard.py
──────────────────────────────────────────────────────────────────────────────
Regression tests: disabled nodes must NOT re-emit signal on subsequent ticks.

Covers the class of bug where a node's tick() bypasses the enabled=False
guard and re-broadcasts power downstream, undoing a user disable action.

For every node type that has a tick() and emits power, we verify:
  1. Disable the source (enabled=False + repropagate_all).
  2. Downstream node is off.
  3. Run N ticks.
  4. Downstream node is STILL off — tick() did not re-emit.
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from power_graph import PowerGraph
from power_graph.node_registry import NodeRegistry


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tick(graph: PowerGraph, steps: int = 10, fps: int = 20):
    dt = 1.0 / fps
    for _ in range(steps):
        for panel in graph.panels:
            cls = NodeRegistry.get(panel['type'])
            if cls:
                cls.tick(panel, dt, graph)
        graph.update_all_gen_draws()


def _minimal_graph(*types):
    """
    Build a minimal graph: chain of nodes of the given types, left-to-right.
    Returns (graph, panels_list).
    """
    g = PowerGraph()
    nodes = [g.spawn(t) for t in types]
    for i in range(len(nodes) - 1):
        g.connect(nodes[i], 0, nodes[i + 1], 0)
    return g, nodes


# ── Generator → Load ──────────────────────────────────────────────────────────

class TestGeneratorEnabledGuard:
    """Generator.tick() must not re-emit when enabled=False."""

    def _live_gen_with_load(self):
        g, (gen, load) = _minimal_graph('gen', 'load')
        gen['live']  = True
        gen['volts'] = 240
        gen['amps']  = 10
        g.emit(gen, {'v': 240, 'a': 10})
        assert load['state'] == 'on', "precondition: load must be on before disable"
        return g, gen, load

    def test_disabled_gen_load_goes_off(self):
        """Disabling a live generator propagates None downstream immediately."""
        g, gen, load = self._live_gen_with_load()
        gen['enabled'] = False
        g.repropagate_all()
        assert load['state'] == 'off'

    def test_disabled_gen_stays_off_after_ticks(self):
        """Load stays off after N ticks — tick() must not re-emit."""
        g, gen, load = self._live_gen_with_load()
        gen['enabled'] = False
        g.repropagate_all()
        _tick(g, steps=40)   # 2 seconds at 20fps
        assert load['state'] == 'off', (
            "Generator.tick() re-emitted signal despite enabled=False"
        )

    def test_re_enable_gen_restores_load(self):
        """Re-enabling a generator restores downstream power via repropagate."""
        g, gen, load = self._live_gen_with_load()
        gen['enabled'] = False
        g.repropagate_all()
        _tick(g, steps=5)
        assert load['state'] == 'off'

        # Re-enable — live is still True, repropagate re-emits the signal
        gen['enabled'] = True
        g.repropagate_all()
        assert load['state'] == 'on'


# ── Series-Battery → Load ─────────────────────────────────────────────────────

class TestSeriesBatteryEnabledGuard:
    """SeriesBattery running=False / enabled=False must cut downstream signal."""

    def _live_battery_with_load(self):
        g, (bat, load) = _minimal_graph('series-battery', 'load')
        # Feed battery a signal so apply() puts it in charge/pass mode
        from power_graph.nodes.series_battery import SeriesBattery
        g.receive(bat, {'v': 12, 'a': 5})
        # If still off (dead battery, cap=0), force passthrough preset
        if load['state'] == 'off':
            # Give it capacity
            bat['chargeAmps'] = 2
            bat['capacityWh'] = 10
            bat['chargeWh']   = 8
            g.receive(bat, {'v': 12, 'a': 5})
        return g, bat, load

    def test_battery_running_false_cuts_signal(self):
        """toggle() (running=False) cuts downstream immediately."""
        g, bat, load = self._live_battery_with_load()
        if load['state'] == 'off':
            pytest.skip("battery in dead/pass state — toggle test not applicable")
        from power_graph.nodes.series_battery import SeriesBattery
        SeriesBattery.toggle(bat, g)
        assert bat['running'] is False
        assert load['state'] == 'off'

    def test_battery_running_false_stays_off_after_ticks(self):
        """Load stays off after ticks — tick() must not re-emit."""
        g, bat, load = self._live_battery_with_load()
        if load['state'] == 'off':
            pytest.skip("battery in dead/pass state")
        from power_graph.nodes.series_battery import SeriesBattery
        SeriesBattery.toggle(bat, g)
        _tick(g, steps=40)
        assert load['state'] == 'off', (
            "SeriesBattery.tick() re-emitted despite running=False"
        )

    def test_battery_enabled_false_cuts_signal(self):
        """enabled=False (graph disconnect) also cuts downstream signal."""
        g, bat, load = self._live_battery_with_load()
        bat['enabled'] = False
        g.repropagate_all()
        _tick(g, steps=40)
        assert load['state'] == 'off', (
            "SeriesBattery re-emitted despite enabled=False"
        )


# ── Breaker → Load ────────────────────────────────────────────────────────────

class TestBreakerEnabledGuard:
    """A disabled or open breaker must not pass signal downstream."""

    def _live_breaker_with_load(self):
        g = PowerGraph()
        gen     = g.spawn('gen')
        breaker = g.spawn('breaker')
        load    = g.spawn('load')
        g.connect(gen, 0, breaker, 0)
        g.connect(breaker, 0, load, 0)
        gen['live']   = True
        gen['volts']  = 240
        gen['amps']   = 10
        breaker['closed'] = True
        g.emit(gen, {'v': 240, 'a': 10})
        assert load['state'] == 'on', "precondition: load must be powered via breaker"
        return g, gen, breaker, load

    def test_breaker_toggle_cuts_load(self):
        from power_graph.nodes.breaker import Breaker
        g, gen, breaker, load = self._live_breaker_with_load()
        Breaker.toggle(breaker, g)
        assert breaker['state'] == 'open'
        assert load['state'] == 'off'

    def test_breaker_disabled_stays_off_after_ticks(self):
        g, gen, breaker, load = self._live_breaker_with_load()
        breaker['enabled'] = False
        g.repropagate_all()
        _tick(g, steps=40)
        assert load['state'] == 'off', (
            "Breaker passed signal despite enabled=False after ticks"
        )


# ── BusBar → Load ─────────────────────────────────────────────────────────────

class TestBusBarEnabledGuard:
    """A disabled bus-bar must cut all output pips."""

    def _live_bus_with_load(self):
        g = PowerGraph()
        gen  = g.spawn('gen')
        bus  = g.spawn('bus-bar', preset={'outputCount': 2, 'weights': [1, 1]})
        load = g.spawn('load')
        g.connect(gen, 0, bus, 0)
        g.connect(bus, 0, load, 0)
        gen['live']  = True
        gen['volts'] = 240
        gen['amps']  = 10
        g.emit(gen, {'v': 240, 'a': 10})
        assert load['state'] == 'on', "precondition: load must be on via bus"
        return g, gen, bus, load

    def test_bus_disabled_cuts_all_outputs(self):
        g, gen, bus, load = self._live_bus_with_load()
        bus['enabled'] = False
        g.repropagate_all()
        assert load['state'] == 'off'

    def test_bus_disabled_stays_off_after_ticks(self):
        g, gen, bus, load = self._live_bus_with_load()
        bus['enabled'] = False
        g.repropagate_all()
        _tick(g, steps=40)
        assert load['state'] == 'off', (
            "BusBar passed signal despite enabled=False after ticks"
        )

    def test_gen_disabled_bus_goes_off(self):
        """Disabling the upstream generator cuts through a bus-bar to its loads."""
        g, gen, bus, load = self._live_bus_with_load()
        gen['enabled'] = False
        g.repropagate_all()
        _tick(g, steps=40)
        assert load['state'] == 'off', (
            "Generator.tick() re-emitted through bus despite enabled=False"
        )


# ── Generic: any node with tick() must respect enabled=False ─────────────────

TICK_EMITTERS = ['gen', 'series-battery']

@pytest.mark.parametrize("node_type", TICK_EMITTERS)
def test_tick_emitter_respects_enabled(node_type):
    """
    Parametric guard: for every node type that has a non-trivial tick(),
    enabling=False must prevent any downstream load from being powered,
    even after many ticks.
    """
    g, (source, load) = _minimal_graph(node_type, 'load')

    # Force source into an active emitting state
    source['live']    = True
    source['enabled'] = True
    source['volts']   = source.get('volts', 240)
    source['amps']    = source.get('amps', 10)
    source['running'] = True   # series-battery
    g.emit(source, {'v': source['volts'], 'a': source['amps']})

    # Disable and repropagate
    source['enabled'] = False
    g.repropagate_all()
    _tick(g, steps=40)

    assert load['state'] == 'off', (
        f"{node_type}.tick() re-emitted signal despite enabled=False"
    )
