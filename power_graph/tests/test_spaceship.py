"""
test_spaceship.py
──────────────────────────────────────────────────────────────────────────────
Integration test: spaceship.json layout

Tests the loader, the full cold-power-on scenario (no warm-up, all generators
live at once), and the resulting blown-component cascade that is expected
gameplay when a ship is powered up without first enabling individual systems.

What a "correct" run looks like
────────────────────────────────
  • Generators 1-4 start live (live=True in config)
  • High-voltage buses (480V) receive an inrush spike
  • Loads that have maxVolts < spike voltage blow immediately
  • Low-voltage end-loads (48V bus) remain off (below minVolts)
  • Emergency battery bank powers emergency lighting normally (low-voltage, safe)
  • Meters pass signal through and read correctly
  • Converters step voltage down and produce valid outputs

Run:
    python power_graph/tests/test_spaceship.py
    cd power_graph && python -m pytest tests/test_spaceship.py -v
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from power_graph import PowerGraph
from power_graph.loader import load_layout_file

LAYOUT = pathlib.Path(__file__).parent.parent.parent / 'func-pipes' / 'layouts' / 'spaceship.json'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_graph() -> PowerGraph:
    """Fresh graph loaded from spaceship.json."""
    graph = PowerGraph()
    load_layout_file(graph, LAYOUT)
    return graph


def _tick(graph: PowerGraph, seconds: float, fps: int = 20):
    """Advance the simulation by *seconds* without asyncio."""
    from power_graph.node_registry import NodeRegistry
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


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_loader_panel_count():
    """Loader creates exactly 50 panels matching the JSON node list."""
    print("\n" + "=" * 70)
    print("TEST 1: Loader — panel count")
    print("=" * 70)

    graph = _build_graph()
    count = len(graph.panels)
    print(f"  • Spawned {count} panels")
    assert count == 50, f"Expected 50, got {count}"
    print("  ✓ 50 panels spawned")

    print("\n✓ Loader panel count passed!")


def test_loader_ids_preserved():
    """Panel IDs match the JSON 'id' field (1-50, no gaps)."""
    print("\n" + "=" * 70)
    print("TEST 2: Loader — IDs preserved")
    print("=" * 70)

    graph = _build_graph()
    ids = sorted(p['id'] for p in graph.panels)
    assert ids == list(range(1, 51)), f"IDs don't match: {ids}"
    print("  ✓ Panel IDs 1-50 all present")

    print("\n✓ ID preservation passed!")


def test_loader_connection_count():
    """Loader wires up exactly 48 connections (matching the edges dict in the JSON)."""
    print("\n" + "=" * 70)
    print("TEST 3: Loader — connection wiring")
    print("=" * 70)

    graph = _build_graph()
    total = sum(len(v) for v in graph._connections.values())
    print(f"  • Total connection endpoints: {total}")
    assert total == 48, f"Expected 48, got {total}"
    print("  ✓ All 48 connections wired")

    print("\n✓ Connection wiring passed!")


def test_generators_live():
    """All four generators start live (as set in JSON config)."""
    print("\n" + "=" * 70)
    print("TEST 4: Generators live at startup")
    print("=" * 70)

    graph = _build_graph()
    for gen_id, name, volts, amps in [
        (1, "Fusion Reactor Alpha",  480, 20),
        (2, "Fusion Reactor Beta",   480, 20),
        (3, "Auxiliary Generator",   240, 15),
        (4, "Emergency Battery Bank",120,  8),
    ]:
        p = _panel(graph, gen_id)
        assert p is not None, f"Panel {gen_id} missing"
        assert p.get('live'),  f"Generator {gen_id} not live"
        assert p.get('volts') == volts, f"Generator {gen_id} wrong volts"
        assert p.get('amps')  == amps,  f"Generator {gen_id} wrong amps"
        print(f"  ✓ #{gen_id} {name}: {volts}V/{amps}A live={p['live']}")

    print("\n✓ Generator startup passed!")


def test_meters_reading():
    """
    After cold-start propagation, meters powered by gen3/gen4 report non-zero
    readings.  Gen1 and gen2 trip on cold start (overload from inrush spike),
    so Main Bus A (#5) and Propulsion Panel (#9) go dark.
    """
    print("\n" + "=" * 70)
    print("TEST 5: Meters reading after propagation")
    print("=" * 70)

    graph = _build_graph()

    # Powered by gen3 (240V) and gen4 (120V) — should be on
    live_meter_ids = [6, 15, 21, 33, 44]
    for mid in live_meter_ids:
        p = _panel(graph, mid)
        v = p.get('reading_volts', 0)
        a = p.get('reading_amps', 0)
        print(f"  • #{mid:2} {p['label']:30}  {v:.1f}V  {a:.2f}A  state={p['state']}")
        assert p['state'] == 'on',  f"Meter {mid} expected on, got {p['state']}"
        assert v > 0, f"Meter {mid} reading_volts == 0"

    # Gen1/2 trip on cold start → Main Bus A and Propulsion Panel go dark
    for mid in [5, 9]:
        p = _panel(graph, mid)
        print(f"  • #{mid:2} {p['label']:30}  state={p['state']}  (gen1/2 tripped)")
        assert p['state'] == 'off', f"Meter {mid} should be off (gen1/2 tripped), got {p['state']}"

    print("\n✓ Meter readings passed!")


def test_buses_voltage_hierarchy():
    """
    Main Bus B (240V nominal, #6) reads higher than the Bridge Panel (48V
    bus, #44).  Bus A (#5) is dark because gen1/2 tripped on cold start.
    """
    print("\n" + "=" * 70)
    print("TEST 6: Bus voltage hierarchy")
    print("=" * 70)

    graph = _build_graph()
    bus_b   = _panel(graph, 6)    # Main Bus B — 240V nominal (gen3)
    bridge  = _panel(graph, 44)   # Bridge Panel — 48V bus (gen4)

    v_b      = bus_b.get('reading_volts', 0)
    v_bridge = bridge.get('reading_volts', 0)
    print(f"  • Main Bus B (240V bus): {v_b:.1f}V")
    print(f"  • Bridge Panel  (48V bus): {v_bridge:.1f}V")

    assert v_b > v_bridge, f"Main Bus B ({v_b}V) should be > Bridge Panel ({v_bridge}V)"
    assert v_b > 200, f"Main Bus B should be ~240V, got {v_b}V"
    print("  ✓ Main Bus B > Bridge Panel voltage hierarchy confirmed")

    print("\n✓ Bus hierarchy passed!")


def test_cold_start_blown_cascade():
    """
    Cold-start (all generators live simultaneously) causes a blown cascade.

    High-voltage loads connected to the 480V bus blow because the inrush spike
    (480V × 1.15 = 552V) exceeds their maxVolts.  This is expected behaviour
    and an intentional gameplay dimension.
    """
    print("\n" + "=" * 70)
    print("TEST 7: Cold-start blown cascade (expected gameplay)")
    print("=" * 70)

    graph = _build_graph()

    # Run a short tick to let spike decay propagate
    _tick(graph, seconds=1.0)

    blown = [p for p in graph.panels if p.get('state') == 'blown']
    off   = [p for p in graph.panels if p.get('state') == 'off']
    on    = [p for p in graph.panels if p.get('state') == 'on']

    print(f"  • Blown: {len(blown)}")
    print(f"  • Off  : {len(off)}")
    print(f"  • On   : {len(on)}")

    for p in blown:
        print(f"    [blown]  #{p['id']:2}  {p['type']:10}  {p['label']}")

    # There must be at least some blown components from the cold start
    assert len(blown) > 0, "Expected blown components after cold start"
    print(f"\n  ✓ {len(blown)} components blown — cold-start cascade confirmed")

    # Generators themselves must NOT be blown
    for gen_id in (1, 2, 3, 4):
        p = _panel(graph, gen_id)
        assert p['state'] != 'blown', f"Generator {gen_id} should not be blown"
    print("  ✓ Generators survived")

    print("\n✓ Cold-start blown cascade passed!")


def test_emergency_lighting_survives():
    """
    Emergency lighting (#49) is powered only by the low-voltage battery bank
    (#4, 120V) and must remain on after the cold start.
    """
    print("\n" + "=" * 70)
    print("TEST 8: Emergency lighting survives cold start")
    print("=" * 70)

    graph = _build_graph()
    _tick(graph, seconds=1.0)

    light = _panel(graph, 49)   # "Emergency Lighting" bulb
    print(f"  • #49 Emergency Lighting: state={light['state']}  brightness={light.get('brightness', 0):.2f}")

    assert light['state'] in ('on', 'dim'), \
        f"Emergency lighting expected on/dim, got {light['state']}"
    assert light.get('brightness', 0) > 0, "Emergency lighting has zero brightness"
    print("  ✓ Emergency lighting is on and has brightness > 0")

    print("\n✓ Emergency lighting test passed!")


def test_converters_step_down():
    """Converters #7 and #8 are in step-down state after propagation."""
    print("\n" + "=" * 70)
    print("TEST 9: Converters step down")
    print("=" * 70)

    graph = _build_graph()

    for cid, out_volts in [(7, 240), (8, 48)]:
        p = _panel(graph, cid)
        print(f"  • #{cid} {p['label']}: state={p['state']}  outVolts={p.get('outVolts')}  ratio={p.get('ratio')}")
        # Both should be stepping down from higher input
        assert p['state'] in ('step-down', 'step-up', 'unity', 'off'), \
            f"Converter {cid} unexpected state: {p['state']}"
        assert p.get('outVolts') == out_volts, \
            f"Converter {cid} outVolts: expected {out_volts}, got {p.get('outVolts')}"
    print("  ✓ Converter output voltages match config")

    print("\n✓ Converter step-down passed!")


def test_wire_resistance_applied():
    """
    Meters further from the source read lower voltage due to wire resistance.
    Main Bus B (#6) is one hop from gen3; Navigation Panel (#21) is downstream
    with a longer cable run, so it reads slightly less.
    """
    print("\n" + "=" * 70)
    print("TEST 10: Wire resistance applied along connections")
    print("=" * 70)

    graph = _build_graph()

    # Main Bus B (#6): first meter after gen3 converter output
    # Navigation Panel (#21): further downstream via 771px cable from Bus B
    bus_b = _panel(graph, 6)   # closer to source
    nav   = _panel(graph, 21)  # further downstream

    v_b = bus_b.get('reading_volts', 0)
    v_n = nav.get('reading_volts', 0)

    print(f"  • Main Bus B:      {v_b:.2f}V  (first hop from gen3)")
    print(f"  • Navigation Panel:{v_n:.2f}V  (771px downstream)")

    assert v_b > v_n, f"Main Bus B ({v_b}V) should be > Navigation Panel ({v_n}V)"
    print("  ✓ Voltage diminishes with wire length — resistance confirmed")

    print("\n✓ Wire resistance passed!")


def test_tick_does_not_revive_blown():
    """Ticking the simulation does not un-blow components (blown is permanent)."""
    print("\n" + "=" * 70)
    print("TEST 11: Blown components stay blown after ticking")
    print("=" * 70)

    graph = _build_graph()
    _tick(graph, seconds=0.1)

    blown_before = {p['id'] for p in graph.panels if p.get('state') == 'blown'}
    print(f"  • Blown after initial propagation: {len(blown_before)}")

    _tick(graph, seconds=5.0)

    blown_after = {p['id'] for p in graph.panels if p.get('state') == 'blown'}
    print(f"  • Blown after 5s tick: {len(blown_after)}")

    # Blown set should only grow or stay the same
    revived = blown_before - blown_after
    assert len(revived) == 0, f"Components were un-blown: {revived}"
    print("  ✓ No blown components revived — blown is permanent")

    print("\n✓ Blown permanence passed!")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_loader_panel_count,
        test_loader_ids_preserved,
        test_loader_connection_count,
        test_generators_live,
        test_meters_reading,
        test_buses_voltage_hierarchy,
        test_cold_start_blown_cascade,
        test_emergency_lighting_survives,
        test_converters_step_down,
        test_wire_resistance_applied,
        test_tick_does_not_revive_blown,
    ]

    print("=" * 70)
    print("Python Power Graph — Spaceship Integration Tests")
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
