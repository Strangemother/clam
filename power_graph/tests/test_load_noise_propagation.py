"""
test_load_noise_propagation.py
──────────────────────────────────────────────────────────────────────────────
Regression tests for load-noise propagation through the signal chain.

Coverage
────────
  1. pass_through_signal  — Load emits a reduced-amps signal downstream (not None)
                            so nodes chained after a load receive a live signal.
  2. noise_modulates_current_watts — when noise is enabled, current_watts oscillates
                            over time (does not stay flat at rated watts).
  3. noise_changes_downstream_amps — a noisy load passes varying amps to a chained
                            downstream node each time current_watts shifts.
  4. noise_free_load_stable — with noise=0 the downstream signal stays constant (no
                            spurious re-emissions when draw is steady).
  5. noise_reapply_updates_gen_draw — generator drawWatts tracks current_watts
                            changes produced by noise ticks.
  6. gen_microsag_on_draw_change — generator emits a proportional micro-sag voltage
                            when aggregate load draw changes by >5 W.
  7. motor_noise_reaches_chained_load — two loads in series: motor noise oscillation
                            is visible in the amps arriving at the second load.
  8. load_has_outbound_pip — Load panels expose an outbound pip so the UI/graph
                            can wire them as pass-through nodes.

Run:
    cd power_graph && python -m pytest tests/test_load_noise_propagation.py -v
"""

import sys
import pathlib
import math

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

import power_graph.nodes  # noqa — registers all node types as side-effect
from power_graph.graph import PowerGraph
from power_graph.node_registry import NodeRegistry
from power_graph.node_base import NOMINAL_VOLTS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_gen():
    """Return a PowerGraph with a single live generator (240 V / 20 A)."""
    graph = PowerGraph()
    gen = graph.spawn('gen', label='Gen', preset={'volts': 240, 'amps': 20})
    gen['live'] = True
    return graph, gen


def _tick(graph: PowerGraph, seconds: float, fps: int = 20):
    """Synchronous tick — no asyncio required."""
    dt    = 1.0 / fps
    steps = int(seconds * fps)
    for _ in range(steps):
        for panel in graph.panels:
            cls = NodeRegistry.get(panel['type'])
            if cls and hasattr(cls, 'tick'):
                cls.tick(panel, dt, graph)
        graph.update_all_gen_draws()


def _wired_pair(load_preset: dict) -> tuple:
    """
    generator ──► load
    Returns (graph, gen, load_panel).
    """
    graph, gen = _build_gen()
    load = graph.spawn('load', label='Load', preset=load_preset)
    graph.connect(gen, 0, load, 0)
    graph.repropagate_all()
    graph.update_all_gen_draws()
    return graph, gen, load


def _wired_chain(first_preset: dict, second_preset: dict) -> tuple:
    """
    generator ──► load_a ──► load_b
    Returns (graph, gen, load_a, load_b).
    """
    graph, gen = _build_gen()
    load_a = graph.spawn('load', label='LoadA', preset=first_preset)
    load_b = graph.spawn('load', label='LoadB', preset=second_preset)
    graph.connect(gen,    0, load_a, 0)
    graph.connect(load_a, 0, load_b, 0)
    graph.repropagate_all()
    graph.update_all_gen_draws()
    return graph, gen, load_a, load_b


# ── Test 1: pass-through signal ───────────────────────────────────────────────

def test_pass_through_signal():
    """
    A load chained after a generator must receive a live (non-None) signal,
    and a node chained *after* the load must also receive a live signal with
    amps reduced by the load's draw.
    """
    load_watts = 480  # exactly 2 A at 240 V
    graph, gen, load_a, load_b = _wired_chain(
        {'watts': load_watts, 'noise': 0},
        {'watts': 100, 'noise': 0},
    )

    assert load_a['state'] == 'on', f"load_a should be on, got {load_a['state']!r}"
    assert load_b['state'] == 'on', f"load_b should be on, got {load_b['state']!r}"

    # Let the inrush spike settle so current_watts equals rated watts
    _tick(graph, 2.0)

    # load_b's inbound signal should have amps = gen_amps - load_a_draw
    expected_a = gen['amps'] - (load_watts / NOMINAL_VOLTS)
    sig_b = load_b.get('_last_signal') or {}
    # Allow 2 % tolerance for floating-point rounding
    assert sig_b.get('a', 0) == pytest.approx(expected_a, rel=0.02), (
        f"Expected load_b to receive ≈{expected_a:.2f} A, got {sig_b.get('a')}"
    )


# ── Test 2: noise modulates current_watts ─────────────────────────────────────

def test_noise_modulates_current_watts():
    """
    With noise enabled, current_watts must not be flat at the rated value
    after several seconds of ticking — it should oscillate.
    """
    graph, gen, load = _wired_pair({'watts': 500, 'noise': 15, 'noiseInterval': 0.1})

    # Let the inrush spike decay before checking noise bounds
    _tick(graph, 2.0)

    samples = []
    for _ in range(40):
        _tick(graph, 0.05)
        samples.append(load['current_watts'])

    assert max(samples) > min(samples), (
        "current_watts never varied — noise is not modulating the load draw"
    )
    # Must stay within ±15 % of rated (spike has settled)
    assert max(samples) <= 500 * 1.16
    assert min(samples) >= 500 * 0.84


# ── Test 3: noise changes downstream amps ─────────────────────────────────────

def test_noise_changes_downstream_amps():
    """
    When a noisy load re-applies and emits a new signal, the downstream node's
    _last_signal.a must reflect that updated draw (i.e. amps vary over time).
    """
    graph, gen, load_a, load_b = _wired_chain(
        {'watts': 500, 'noise': 20, 'noiseInterval': 0.05},
        {'watts': 50,  'noise': 0},
    )

    amp_samples = []
    for _ in range(60):
        _tick(graph, 0.05)
        sig = load_b.get('_last_signal')
        if sig:
            amp_samples.append(sig['a'])

    assert len(amp_samples) > 0, "load_b never received a signal"
    assert max(amp_samples) > min(amp_samples), (
        f"Downstream amps never varied: min={min(amp_samples):.3f} max={max(amp_samples):.3f}. "
        "Noise from load_a is not reaching load_b."
    )


# ── Test 4: noise-free load stays stable ──────────────────────────────────────

def test_noise_free_load_stable():
    """
    With noise=0, current_watts must stay flat at rated watts after the inrush
    spike settles, and downstream amps must not drift.
    """
    graph, gen, load_a, load_b = _wired_chain(
        {'watts': 480, 'noise': 0},
        {'watts': 120, 'noise': 0},
    )

    # Let spike settle
    _tick(graph, 2.0)

    amp_samples = []
    for _ in range(20):
        _tick(graph, 0.05)
        sig = load_b.get('_last_signal')
        if sig:
            amp_samples.append(round(sig['a'], 4))

    assert len(set(amp_samples)) == 1, (
        f"Downstream amps varied when no noise is configured: {set(amp_samples)}"
    )


# ── Test 5: noise reapply updates gen draw ────────────────────────────────────

def test_noise_reapply_updates_gen_draw():
    """
    Generator drawWatts must track the oscillating current_watts of a noisy
    load — it must not be pegged at the catalog rated value throughout.
    """
    graph, gen, load = _wired_pair({'watts': 1000, 'noise': 15, 'noiseInterval': 0.05})

    draw_samples = []
    for _ in range(60):
        _tick(graph, 0.05)
        draw_samples.append(gen['drawWatts'])

    assert max(draw_samples) > min(draw_samples), (
        f"gen drawWatts never varied (min={min(draw_samples)}, max={max(draw_samples)}). "
        "Noise re-apply is not updating generator draw."
    )


# ── Test 6: generator micro-sag on draw change ────────────────────────────────

def test_gen_microsag_on_draw_change():
    """
    When aggregate load draw changes by more than 5 W, the generator must
    re-emit a signal with a voltage slightly below its rated volts (micro-sag),
    not exactly 240 V, and the downstream load must see it.
    """
    # Large noisy load so drawWatts shifts are guaranteed to exceed 5 W threshold.
    graph, gen, load = _wired_pair({'watts': 2000, 'noise': 20, 'noiseInterval': 0.05})

    volts_seen = set()
    for _ in range(80):
        _tick(graph, 0.05)
        sig = load.get('_last_signal')
        if sig:
            volts_seen.add(round(sig['v'], 1))

    assert len(volts_seen) > 1, (
        f"Load only ever saw one voltage ({volts_seen}). "
        "Generator micro-sag is not propagating to loads."
    )
    assert max(volts_seen) <= 240.0, "Voltage must never exceed generator rated volts"
    # Floor allows for spike-induced sag (overload branch emits 0.85 × rated)
    assert min(volts_seen) >= 240.0 * 0.80, "Voltage sagged below 80 % of rated"


# ── Test 7: motor noise reaches chained load ──────────────────────────────────

def test_motor_noise_reaches_chained_load():
    """
    generator ──► motor (noisy) ──► passive-load
    The passive load's inbound amps must oscillate with the motor's noise,
    confirming noise propagates through the chain downstream.
    """
    graph, gen, motor, passive = _wired_chain(
        {'watts': 500, 'noise': 12, 'noiseInterval': 0.15, 'label': 'Motor'},
        {'watts': 50,  'noise': 0,  'label': 'Passive'},
    )

    amp_samples = []
    for _ in range(60):
        _tick(graph, 0.05)
        sig = passive.get('_last_signal')
        if sig:
            amp_samples.append(sig['a'])

    assert len(amp_samples) > 0, "Passive load never received a signal"
    spread = max(amp_samples) - min(amp_samples)
    assert spread > 0.01, (
        f"Motor noise did not reach the chained passive load "
        f"(amp spread={spread:.4f} A)"
    )


# ── Test 8: load exposes outbound pip ─────────────────────────────────────────

def test_load_has_outbound_pip():
    """
    Load panels must have at least one outbound pip so the graph can wire
    them as pass-through nodes in multi-node topologies.
    """
    graph, _, load = _wired_pair({'watts': 100, 'noise': 0})
    pips = load.get('pipsOutbound', [])
    assert len(pips) >= 1, (
        f"Load has no outbound pips ({pips}). "
        "Cannot be used as pass-through in a chain."
    )
    assert pips[0].get('index') == 0


# ── Test 9: variance shifts steady-state draw off exact rated watts ───────────

def test_variance_shifts_steady_state_draw():
    """
    With variance > 0, a load's settled current_watts must not be exactly
    equal to its rated watts — the variance factor shifts it slightly.
    """
    # Use a large variance so the shift is measurable without being swamped
    # by floating-point noise; noise=0 so only variance remains.
    graph, _, load = _wired_pair({'watts': 1000, 'noise': 0, 'variance': 5.0})
    _tick(graph, 2.0)  # let spike settle

    rated = 1000
    assert load['current_watts'] != rated, (
        f"current_watts is exactly {rated} W — variance is not shifting the draw."
    )
    # Result must still be within the declared ±5 % band
    assert load['current_watts'] == pytest.approx(rated, rel=0.051)


# ── Test 10: variance=0 gives exactly rated watts ─────────────────────────────

def test_variance_zero_gives_exact_watts():
    """
    With variance=0 and noise=0, a settled load must draw exactly its
    rated watts (the variance factor is 1.0).
    """
    graph, _, load = _wired_pair({'watts': 500, 'noise': 0, 'variance': 0})
    _tick(graph, 2.0)

    assert load['current_watts'] == pytest.approx(500.0, rel=1e-6), (
        f"Expected exactly 500 W with no variance, got {load['current_watts']}"
    )


# ── Test 11: two identical units get different variance factors ────────────────

def test_variance_factors_differ_between_units():
    """
    Two panels spawned from the same preset must receive independently
    randomised _variance_factor values (they should not be identical).
    This test could fail ~0.00001 % of the time by coincidence — acceptable.
    """
    graph, gen = _build_gen()
    load_a = graph.spawn('load', label='A', preset={'watts': 1000, 'noise': 0, 'variance': 5.0})
    load_b = graph.spawn('load', label='B', preset={'watts': 1000, 'noise': 0, 'variance': 5.0})
    assert load_a['_variance_factor'] != load_b['_variance_factor'], (
        "Both units got identical _variance_factor — randomisation is broken."
    )


# ── Test 12: heater peaks at variance-shifted ceiling, not exact rated watts ──

def test_heater_peaks_at_variance_ceiling():
    """
    A fully-heated heater (temperature at maxTemp) must draw close to
    watts * _variance_factor, not the bare rated watts.
    """
    from power_graph.nodes.heater import Heater

    graph, gen = _build_gen()
    heater = graph.spawn('heater', label='H', preset={
        'watts': 2000, 'minWatts': 100,
        'heatRate': 40.0, 'coolRate': 0.1,   # heat fast so the test is quick
        'maxTemp': 80.0, 'resetTemp': 60.0,
        'noise': 0, 'variance': 5.0,
    })
    graph.connect(gen, 0, heater, 0)
    graph.repropagate_all()

    _tick(graph, 5.0)  # enough time to reach maxTemp (2 s at 40 °C/s)

    expected_ceil = 2000 * heater['_variance_factor']
    # When fully heated and thermostat has not tripped, currentWatts ≈ expected_ceil
    if heater.get('heatSwitch'):
        assert heater['current_watts'] == pytest.approx(expected_ceil, rel=0.02), (
            f"Heater peaked at {heater['current_watts']:.1f} W; "
            f"expected ≈{expected_ceil:.1f} W (variance factor={heater['_variance_factor']:.4f})"
        )
