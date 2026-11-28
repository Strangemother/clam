"""
test_heater_thermal.py
──────────────────────────────────────────────────────────────────────────────
Unit tests for Heater thermal behaviour.

Coverage
────────
  1. Minimum draw  — heater always pulls at least minWatts from the generator,
                     even when newly connected and cold.
  2. Warm-up ramp  — current_watts rises from minWatts toward rated watts as
                     temperature climbs; never stays flat at full rated watts.
  3. Thermostat trip — heatSwitch goes False and draw drops to minWatts once
                       temperature reaches maxTemp.
  4. Thermostat reset & re-ramp — heatSwitch re-enables at resetTemp, draw
                                   starts back at minWatts and climbs again.
  5. Cycle repeat  — the trip/reset/ramp cycle happens at least twice,
                     confirming the oscillation is stable and unbounded.

Run:
    cd power_graph && python -m pytest tests/test_heater_thermal.py -v
"""

import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

import power_graph.nodes  # noqa — registers all node types as side-effect
from power_graph.graph import PowerGraph
from power_graph.node_registry import NodeRegistry


# ── Helpers ───────────────────────────────────────────────────────────────────

PRESET = {
    'watts':         1000,
    'minWatts':      50,
    'heatRate':      20.0,   # fast — reaches maxTemp in 4 simulated seconds
    'coolRate':      15.0,   # fast cool-down
    'maxTemp':       80.0,
    'resetTemp':     40.0,
    'noise':         0,      # noise off so draw is deterministic in these tests
    'noiseInterval': 1.0,
}


def _build() -> tuple:
    """
    Return (graph, gen_panel, heater_panel) — a minimal wired graph:
        generator (live) ──► heater
    """
    graph = PowerGraph()

    # Spawn generator, then enable it (live defaults to False)
    gen = graph.spawn('gen', label='Test Gen', preset={
        'volts': 240,
        'amps':  20,
    })
    gen['live'] = True

    # Spawn heater
    heater = graph.spawn('heater', label='Test Heater', preset=PRESET)

    # Wire gen pip-0 → heater pip-0
    graph.connect(gen, 0, heater, 0)
    graph.repropagate_all()
    graph.update_all_gen_draws()

    return graph, gen, heater


def _tick(graph: PowerGraph, seconds: float, fps: int = 20) -> None:
    """Advance the simulation by *seconds* at *fps* without asyncio."""
    dt    = 1.0 / fps
    steps = int(seconds * fps)
    for _ in range(steps):
        for panel in graph.panels:
            node_cls = NodeRegistry.get(panel['type'])
            if node_cls and hasattr(node_cls, 'tick'):
                node_cls.tick(panel, dt, graph)
        graph.update_all_gen_draws()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_minimum_draw_when_cold():
    """
    Immediately after connection the heater must draw at least minWatts.
    current_watts (read by the generator BFS) must never be 0 while powered.
    """
    graph, gen, heater = _build()

    assert heater['state'] in ('on', 'brownout'), \
        f"Heater should be powered after connection, got state={heater['state']!r}"

    assert heater['current_watts'] >= PRESET['minWatts'] * 0.99, (
        f"Cold heater current_watts={heater['current_watts']} "
        f"is below minWatts={PRESET['minWatts']}"
    )

    assert gen['drawWatts'] >= PRESET['minWatts'] * 0.99, (
        f"Generator drawWatts={gen['drawWatts']} should reflect at least minWatts"
    )


def test_warmup_ramp():
    """
    Over the warm-up period current_watts must climb from near minWatts toward
    rated watts.  We sample draws at t=0 and t=2s and require an increase.
    """
    graph, gen, heater = _build()

    draw_cold = heater['current_watts']

    _tick(graph, 2.0)

    draw_warm = heater['current_watts']

    assert draw_warm > draw_cold, (
        f"Draw should increase as heater warms: cold={draw_cold} warm={draw_warm}"
    )
    assert draw_warm < PRESET['watts'] * 1.01, (
        f"Draw must not exceed rated watts: draw_warm={draw_warm}"
    )

    # Generator must track the rising load
    assert gen['drawWatts'] >= draw_warm * 0.99, (
        f"Generator drawWatts={gen['drawWatts']} should track heater draw={draw_warm}"
    )


def test_thermostat_trips_at_max_temp():
    """
    heatSwitch must become False and draw must fall to ≈minWatts once
    temperature reaches maxTemp.
    """
    graph, gen, heater = _build()

    # Run long enough to hit maxTemp (heatRate=20 °C/s, band is 80-20=60 °C → ~3s)
    _tick(graph, 5.0)

    assert heater['temperature'] >= PRESET['maxTemp'] - 1 or not heater['heatSwitch'], (
        "After 5 s the heater should have hit maxTemp or tripped"
    )

    # Force it fully hot if somehow still climbing
    heater['temperature'] = PRESET['maxTemp'] + 1
    _tick(graph, 0.1)

    assert heater['heatSwitch'] is False, \
        f"heatSwitch should be False after maxTemp, got {heater['heatSwitch']}"

    assert heater['heatState'] == 'hot', \
        f"heatState should be 'hot', got {heater['heatState']!r}"

    # Draw must have dropped to minWatts
    assert heater['current_watts'] <= PRESET['minWatts'] * 1.05, (
        f"After trip, current_watts={heater['current_watts']} "
        f"should be ≈minWatts={PRESET['minWatts']}"
    )

    assert gen['drawWatts'] <= PRESET['minWatts'] * 1.1, (
        f"Generator drawWatts={gen['drawWatts']} should reflect minWatts after trip"
    )


def test_thermostat_resets_and_reramps():
    """
    After cooling to resetTemp the thermostat re-enables, draw resumes from
    ≈minWatts, and starts climbing again — not jumping straight to full watts.
    """
    graph, gen, heater = _build()

    # Force the heater into the tripped state
    heater['temperature'] = PRESET['maxTemp'] + 1
    _tick(graph, 0.1)   # trip
    assert heater['heatSwitch'] is False

    draw_after_trip = heater['current_watts']

    # Cool down to just above resetTemp — heatSwitch should re-enable
    heater['temperature'] = PRESET['resetTemp'] - 1
    _tick(graph, 0.1)   # reset

    assert heater['heatSwitch'] is True, \
        "heatSwitch should re-enable after cooling to resetTemp"

    draw_at_reset = heater['current_watts']

    # At the moment of re-enable, draw must be near minWatts — NOT a spike
    assert draw_at_reset <= PRESET['minWatts'] * 1.5, (
        f"Draw at thermostat reset should be near minWatts={PRESET['minWatts']}, "
        f"got {draw_at_reset}"
    )

    # Advance a little — draw should now start climbing again
    _tick(graph, 1.0)
    draw_ramp = heater['current_watts']

    assert draw_ramp > draw_at_reset, (
        f"Draw should ramp after reset: at_reset={draw_at_reset} ramp={draw_ramp}"
    )


def test_thermal_cycle_repeats():
    """
    The heater must complete at least two full trip→reset→ramp cycles,
    demonstrating stable oscillation without drift or stall.
    """
    graph, gen, heater = _build()

    trips = 0
    resets = 0
    prev_switch = True
    # Simulate up to 30 s — with heatRate=20 and coolRate=15 two cycles ~= 10 s
    for _ in range(30 * 20):
        _tick(graph, 1.0 / 20)

        curr_switch = heater['heatSwitch']
        if prev_switch and not curr_switch:
            trips += 1
        elif not prev_switch and curr_switch:
            resets += 1
        prev_switch = curr_switch

        if trips >= 2 and resets >= 2:
            break

    assert trips >= 2, f"Expected ≥2 thermostat trips, got {trips}"
    assert resets >= 2, f"Expected ≥2 thermostat resets, got {resets}"

    # Generator draw must never have gone to zero during the test
    # (we check the final state; individual ticks are tested above)
    assert gen['drawWatts'] >= PRESET['minWatts'] * 0.99 or heater['state'] != 'on', \
        f"Generator drawWatts={gen['drawWatts']} dropped to zero mid-cycle"


# ── Standalone runner ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_minimum_draw_when_cold,
        test_warmup_ramp,
        test_thermostat_trips_at_max_temp,
        test_thermostat_resets_and_reramps,
        test_thermal_cycle_repeats,
    ]
    passed = failed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f'  ✓  {name}')
            passed += 1
        except AssertionError as e:
            print(f'  ✗  {name}: {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
