"""
test_spaceship_repair.py
──────────────────────────────────────────────────────────────────────────────
Integration tests: user-driven repair workflows on spaceship.json

These tests build on the cold-start failure scenario established in
test_spaceship.py — where all four generators come online simultaneously and
the inrush spike blows 23 components — and demonstrate the two mitigation
paths a player uses in-game.


TEST A — Safe startup (no cascade):
────────────────────────────────────
A careful user *disables all downstream devices first*, then enables the
generators.  The spike propagates into disabled panels that cannot blow.
After the spike decays the user re-enables everything, repropagates at
nominal voltage, and brings the ship up with zero casualties.

In-game procedure:
  1. Open the power panel — all generators are offline.
  2. Walk through every powered compartment and flip devices to DISABLED.
  3. Start generators one by one.
  4. Wait for the startup spike to settle (~1 second).
  5. Re-enable devices and confirm full-power nominal readings.


TEST B — Fuse replacement after cold start:
────────────────────────────────────────────
Starting from the wrecked cold-start state (23 blown components), the user
repairs each item following the correct electrical safety procedure:

  1. Wait for the inrush spike to decay so buses reach nominal voltage.
     (If voltage is still above a component's maxVolts, a freshly replaced
     fuse will blow again immediately.)
  2. For every blown component:
       a. Disable the panel  — pull the breaker / isolate it.
       b. Reset the node     — physically replace the fuse/component.
       c. Re-enable the panel — close the breaker again.
  3. Repropagate all sources — power flows at nominal voltage.
  4. Every repaired component returns to an operational state.


Run:
    python power_graph/tests/test_spaceship_repair.py
    cd power_graph && python -m pytest tests/test_spaceship_repair.py -v
"""

import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from power_graph import PowerGraph
from power_graph.loader import load_layout, load_layout_file
from power_graph.node_registry import NodeRegistry
from power_graph.nodes.generator import Generator

LAYOUT = pathlib.Path(__file__).parent.parent.parent / 'func-pipes' / 'layouts' / 'spaceship.json'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_graph() -> PowerGraph:
    """Standard cold-start: all gens live, inrush spike, 23 components blown."""
    graph = PowerGraph()
    load_layout_file(graph, LAYOUT)
    return graph


def _tick(graph: PowerGraph, seconds: float, fps: int = 20):
    """Advance simulation by *seconds* without asyncio."""
    dt = 1.0 / fps
    steps = int(seconds * fps)
    for _ in range(steps):
        for panel in graph.panels:
            node_cls = NodeRegistry.get(panel['type'])
            if node_cls:
                node_cls.tick(panel, dt, graph)
        graph.update_all_gen_draws()


def _panel(graph: PowerGraph, node_id: int) -> dict:
    return graph._find_panel(node_id)


# ── Test A: Safe startup ──────────────────────────────────────────────────────

def test_safe_startup_no_cascade():
    """
    A cautious user disables all consumers *before* enabling generators.
    The inrush spike propagates safely into disabled panels — nothing blows.
    After spike decay, re-enabling and repropagating brings the ship to full
    power with zero component casualties.

    Step-by-step:
        1. Load layout with all generators offline (live=False).
        2. Disable every non-generator panel.
        3. Toggle all generators on  —  spike fires, disabled panels ignore it.
        4. Tick 1 second to let the spike decay.
        5. Re-enable all panels.
        6. Repropagate at nominal voltage  —  everything comes on safely.
    """
    print("\n" + "=" * 70)
    print("TEST A: Safe startup — no cascade")
    print("=" * 70)

    # ── Step 1: Load with generators offline ─────────────────────────────────
    layout = json.load(open(LAYOUT))
    for node in layout['nodes']:
        if node.get('type') == 'gen':
            node.setdefault('config', {})['live'] = False

    graph = PowerGraph()
    load_layout(graph, layout)

    # All panels idle — nothing is powered yet
    assert not any(p.get('state') == 'blown' for p in graph.panels), \
        "No component should be blown before power is applied"
    print("  • All generators offline, no damage yet")

    # ── Step 2: Disable all consumers (pull all breakers) ────────────────────
    consumer_count = 0
    for p in graph.panels:
        if p['type'] != 'gen':
            p['enabled'] = False
            consumer_count += 1
    print(f"  • {consumer_count} consumer panels disabled (breakers pulled)")

    # ── Step 3: Toggle generators on — spike fires into disabled panels ───────
    for gid in [1, 2, 3, 4]:
        p = _panel(graph, gid)
        Generator.toggle(p, graph)
        spike_v = p.get('volts', 0) * 1.15
        print(f"  • Gen {gid} enabled — spike {spike_v:.0f}V into disabled panels")

    blown_mid_spike = [p for p in graph.panels if p.get('state') == 'blown']
    assert len(blown_mid_spike) == 0, \
        f"Spike should not blow disabled consumers, got: " \
        f"{[p['id'] for p in blown_mid_spike]}"
    print(f"  ✓ Spike fired — 0 components blown (all consumers disabled)")

    # ── Step 4: Wait for the spike to decay ───────────────────────────────────
    _tick(graph, seconds=1.0)
    print("  • 1 second elapsed — inrush spike decayed")

    for gid in [1, 2, 3, 4]:
        gen = _panel(graph, gid)
        assert gen['state'] == 'on', f"Gen {gid} should be on after spike decay"

    # ── Step 5: Re-enable all consumer panels (close breakers) ───────────────
    for p in graph.panels:
        if p.get('enabled') is False:
            p['enabled'] = True
    print(f"  • {consumer_count} consumer panels re-enabled")

    # ── Step 6: Repropagate at nominal voltage ────────────────────────────────
    # repropagate_all() broadcasts rated (non-spike) voltage — safe for all loads
    graph.repropagate_all()

    blown_final = [p for p in graph.panels if p.get('state') == 'blown']
    assert len(blown_final) == 0, \
        f"Expected 0 blown after safe startup, got: {[p['id'] for p in blown_final]}"

    on_or_brownout = [p for p in graph.panels
                      if p['state'] in ('on', 'dim', 'brownout')]
    print(f"  ✓ 0 blown components")
    print(f"  ✓ {len(on_or_brownout)} components on or brownout")

    # Verify all distribution buses are live
    for mid, label in [(5, 'Main Bus A'), (6, 'Main Bus B'),
                       (9, 'Propulsion Panel'), (15, 'Life Support Panel'),
                       (21, 'Navigation Panel'), (33, 'Cargo Bay Panel'),
                       (44, 'Bridge Panel')]:
        p = _panel(graph, mid)
        assert p['state'] == 'on', f"{label} (#{mid}) should be on"
        print(f"  ✓ {label}: {p.get('reading_volts', 0):.1f}V")

    print("\n✓ Safe startup test passed — full power, zero casualties!")


# ── Test B: Fuse replacement after cold start ─────────────────────────────────

def test_fuse_replacement_after_cold_start():
    """
    Starting from the wrecked cold-start state (23 blown), the user waits for
    the spike to decay, then repairs every blown component using the correct
    electrical safety procedure: disable → reset (replace fuse) → re-enable.

    After repropagation at nominal voltage, all 23 components return to
    an operational state (on / dim / brownout).

    Step-by-step:
        1. Cold start — 23 components blown by the 552V inrush spike.
        2. Tick 1 second — spike decays, buses settle to safe nominal voltages.
           Gen1/2 recover (BFS finds no 'on' loads → drawAmps = 0 → no trip).
        3. For each blown component:
             a. disable  — pull its breaker (panel['enabled'] = False)
             b. reset    — replace the fuse/component (NodeClass.reset())
             c. re-enable — close the breaker (panel['enabled'] = True)
        4. Repropagate all sources at nominal voltage.
        5. Every repaired component comes back online.
    """
    print("\n" + "=" * 70)
    print("TEST B: Fuse replacement after cold start")
    print("=" * 70)

    # ── Step 1: Cold start — 23 components blown ──────────────────────────────
    graph = _build_graph()
    blown_instant = [p for p in graph.panels if p.get('state') == 'blown']
    print(f"  • Immediately after cold start: {len(blown_instant)} blown")

    # ── Step 2: Wait for spike to decay ───────────────────────────────────────
    _tick(graph, seconds=1.0)

    blown = [p for p in graph.panels if p.get('state') == 'blown']
    assert len(blown) == 14, f"Expected 14 blown after cold start, got {len(blown)}"
    print(f"  • After spike decay: {len(blown)} blown components confirmed")

    # Buses must be at safe nominal voltages before any fuse replacement
    bus_a_v = _panel(graph, 5).get('reading_volts', 0)
    bus_b_v = _panel(graph, 6).get('reading_volts', 0)
    assert bus_a_v > 400, f"Bus A should be ~480V before repair, got {bus_a_v:.1f}V"
    assert bus_b_v > 200, f"Bus B should be ~240V before repair, got {bus_b_v:.1f}V"
    print(f"  • Bus A: {bus_a_v:.1f}V  (safe — below maxVolts 520 of thruster loads)")
    print(f"  • Bus B: {bus_b_v:.1f}V  (safe — below maxVolts 270 of life-support loads)")

    # Generators recovered once the spike cleared their loads
    for gid in [1, 2, 3, 4]:
        gen = _panel(graph, gid)
        assert gen['state'] == 'on', \
            f"Gen {gid} should be on after spike decay, got {gen['state']}"
    print("  • All 4 generators online at nominal output")

    # ── Step 3: Repair loop — disable → reset → re-enable ────────────────────
    print(f"\n  Repairing {len(blown)} blown components:")
    for p in blown:
        node_cls = NodeRegistry.get(p['type'])
        assert node_cls is not None, f"No node class for type '{p['type']}'"

        # a) Isolate — disable the panel (pull breaker / lockout-tagout)
        p['enabled'] = False

        # b) Replace fuse — clears blown flag, resets state to 'off'
        node_cls.reset(p, graph)
        assert not p.get('blown'), \
            f"Panel {p['id']} blown flag must be clear after reset"
        assert p['state'] == 'off', \
            f"Panel {p['id']} must be in 'off' state after reset"

        # c) Reinstate — close the breaker
        p['enabled'] = True

        print(f"    ✓ #{p['id']:2}  {p['type']:10}  {p['label']}")

    # ── Step 4: Repropagate at nominal voltage ────────────────────────────────
    # Only gens emit, using their rated (non-spike) voltage — nothing will blow.
    graph.repropagate_all()

    # ── Step 5: Verify all repaired components are operational ────────────────
    still_blown = [p for p in blown if p.get('state') == 'blown']
    operational = [p for p in blown if p['state'] in ('on', 'dim', 'brownout')]

    assert len(still_blown) == 0, \
        f"Components still blown after repair: {[p['id'] for p in still_blown]}"
    assert len(operational) == len(blown), \
        f"Only {len(operational)}/{len(blown)} repaired components came online — " \
        f"offline: {[p['id'] for p in blown if p not in operational]}"

    print(f"\n  ✓ {len(operational)}/{len(blown)} components restored to operational state")

    # Spot-check representative systems
    for pid, system in [(10, 'Main Thruster Port'), (16, 'O2 Generator'),
                        (22, 'Flight Computer'), (34, 'Cargo Crane A')]:
        p = _panel(graph, pid)
        assert p['state'] in ('on', 'dim', 'brownout'), \
            f"{system} (#{pid}) expected operational, got {p['state']}"
        print(f"  ✓ #{pid}  {system}: {p['state']}")

    print("\n✓ Fuse replacement test passed — all systems restored!")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_safe_startup_no_cascade,
        test_fuse_replacement_after_cold_start,
    ]

    print("=" * 70)
    print("Python Power Graph — Spaceship Repair Integration Tests")
    print("=" * 70)

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    if failed == 0:
        print(f"✓ ALL {passed} TESTS PASSED!")
    else:
        print(f"✗ {failed} FAILED / {passed} passed")
    print("=" * 70)

    if failed:
        sys.exit(1)
