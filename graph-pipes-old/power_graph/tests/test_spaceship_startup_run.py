"""
test_spaceship_startup_run.py
──────────────────────────────────────────────────────────────────────────────
Integration test: 15-second safe-startup simulation of the spaceship power
system running on auxiliary power only (Gen3 + Gen4).  Fusion reactors Gen1
and Gen2 are kept offline, so all downstream load attribution is clean and
each generator owns its loads without BFS double-counting through converters.

Scenario: "Auxiliary power mode"
  • Gen 3  Auxiliary Generator (240V, boosted to 50A for standalone ops)
            Powers all life-support, comms, cargo, secondary systems.
            Loads include heaters with thermal cycling and multiple ripple
            loads — producing dynamic, varying draw throughout the run.
  • Gen 4  Emergency Battery Bank (120V, 8A)
            Powers Emergency Lighting (#49) and UPS (#50) only.
            Draw should be small and relatively stable.
  • Gen 1/2 Fusion Reactors — OFFLINE (propulsion, shields all off)

What this test exercises
────────────────────────
  1. Safe power-on — consumers disabled, then Gen3+Gen4 come online.
     Inrush spike propagates into disabled panels — nothing blows.
  2. Spike decay (1 s) — both generators settle to nominal before
     consumers are re-enabled.
  3. Live operational monitoring — Gen3 and Gen4 polled every 0.25 s for
     15 seconds.
  4. Dynamic draw — ripple and heater thermal cycling on Gen3's bus drive
     measurable variation in drawWatts over time:
       • O2 Generator (#16)     — heater, thermal cycling + 15% ripple
       • CO2 Scrubber (#17)     — 10% ripple
       • Long-Range Comms (#24) — 40% ripple
       • Radar Array (#26)      — 20% ripple
       • Cargo Cranes (#34/#35) — 40% ripple each
       • Cargo Door Motor (#38) — 30% ripple
  5. Gen4 stability — despite surrounding noise, emergency battery holds
     a steady load below its rated 960 W.

Run:
    python power_graph/tests/test_spaceship_startup_run.py
    cd power_graph && python -m pytest tests/test_spaceship_startup_run.py -v -s
"""

import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from power_graph import PowerGraph
from power_graph.loader import load_layout
from power_graph.node_registry import NodeRegistry
from power_graph.nodes.generator import Generator

LAYOUT = pathlib.Path(__file__).parent.parent.parent / 'func-pipes' / 'layouts' / 'spaceship.json'

FPS             = 20     # ticks per second
DURATION        = 15.0   # seconds (enough for heater thermal cycle to start)
SAMPLE_INTERVAL = 0.25   # seconds between telemetry snapshots

# Gen3 standalone amps: JSON is 15A (designed for dual-gen operation with Gen1/2).
# For auxiliary-only mode we boost to 50A (240V x 50A = 12kW) so it can carry
# all 7138W of life-support + comms + cargo without tripping.
GEN3_STANDALONE_AMPS = 50


# ── Helpers ───────────────────────────────────────────────────────────────────

def _panel(graph: PowerGraph, node_id: int) -> dict:
    return graph._find_panel(node_id)


def _tick(graph: PowerGraph, seconds: float, fps: int = FPS):
    dt    = 1.0 / fps
    steps = int(seconds * fps)
    for _ in range(steps):
        for panel in graph.panels:
            node_cls = NodeRegistry.get(panel['type'])
            if node_cls:
                node_cls.tick(panel, dt, graph)
        graph.update_all_gen_draws()


def _safe_startup_aux(graph: PowerGraph) -> int:
    """
    Start only Gen3 and Gen4 (auxiliary power mode).

    Steps:
      1. Disable all non-generator panels.
      2. Toggle Gen3 and Gen4 on  (spike fires into disabled loads).
      3. Tick 1 s to let the spike decay.
      4. Re-enable all panels.
      5. Repropagate at nominal voltage.
         Loads on Gen1/Gen2-exclusive paths (propulsion, shields) get no
         power source and settle to 'off' -- that is correct behaviour.
    """
    consumer_ids = []
    for p in graph.panels:
        if p['type'] != 'gen':
            p['enabled'] = False
            consumer_ids.append(p['id'])

    # Start Gen3 and Gen4 only
    for gid in [3, 4]:
        gen = _panel(graph, gid)
        Generator.toggle(gen, graph)

    _tick(graph, 1.0)

    for p in graph.panels:
        if p['id'] in consumer_ids:
            p['enabled'] = True

    graph.repropagate_all()
    return len(consumer_ids)


def _snapshot(t: float, graph: PowerGraph, g3: dict, g4: dict,
              o2: dict, note: str = '') -> dict:
    return {
        't':       round(t, 3),
        'g3_W':    round(g3.get('drawWatts', 0.0), 1),
        'g4_W':    round(g4.get('drawWatts', 0.0), 1),
        'g3_st':   g3.get('state', '?'),
        'g4_st':   g4.get('state', '?'),
        'o2_temp': round(o2.get('temperature', 0.0), 1),
        'note':    note,
    }


# ── Test ──────────────────────────────────────────────────────────────────────

def test_startup_run_15s():
    """
    Boot the spaceship in auxiliary-power mode (Gen3+Gen4 only) and run for
    15 seconds.  Ripple loads and heater thermal cycling on Gen3's bus create
    measurable draw variation.  Gen4 serves a small stable emergency load.

    Assertions:
      - Safe startup: 0 blown.
      - Gen3 and Gen4 stay 'on' throughout.
      - Gen3 draw varies >= 50 W over the run (ripple + heater cycling).
      - Gen4 draw > 0 and stays below rated 960 W.
      - O2 Generator (#16) heats up (thermal cycling is active).
    """
    print("\n" + "=" * 76)
    print("TEST: 15-second auxiliary-power startup run (Gen3 + Gen4)")
    print("=" * 76)

    # ── Build layout with all gens offline and Gen3 boosted ──────────────────
    layout = json.load(open(LAYOUT))
    for node in layout['nodes']:
        if node.get('type') == 'gen':
            cfg = node.setdefault('config', {})
            cfg['live'] = False
            if node['id'] == 3:
                cfg['amps'] = GEN3_STANDALONE_AMPS

    graph = PowerGraph()
    load_layout(graph, layout)

    # ── Auxiliary safe startup ────────────────────────────────────────────────
    n_consumers = _safe_startup_aux(graph)

    blown = [p for p in graph.panels if p.get('state') == 'blown']
    assert len(blown) == 0, \
        f"Safe startup should blow 0 components, got: {[p['id'] for p in blown]}"
    print(f"  ok  Auxiliary safe startup -- {n_consumers} consumers re-enabled, 0 blown")

    on_count       = sum(1 for p in graph.panels if p.get('state') in ('on', 'dim'))
    brownout_count = sum(1 for p in graph.panels if p.get('state') == 'brownout')
    off_count      = sum(1 for p in graph.panels
                         if p.get('state') == 'off' and p['type'] != 'gen')
    print(f"  ok  {on_count} on/dim,  {brownout_count} brownout,"
          f"  {off_count} off (no-source -- propulsion/shields offline),  0 blown")

    # ── Set up telemetry ──────────────────────────────────────────────────────
    g3 = _panel(graph, 3)
    g4 = _panel(graph, 4)
    o2 = _panel(graph, 16)   # O2 Generator -- heater, thermal cycling

    assert g3 is not None, "Gen3 not found"
    assert g4 is not None, "Gen4 not found"
    assert o2 is not None, "O2 Generator (#16) not found"

    dt           = 1.0 / FPS
    steps        = int(DURATION * FPS)
    sample_every = max(1, int(SAMPLE_INTERVAL * FPS))
    snapshots    = []

    print(f"\n  {'t':>6}  {'Gen3_W':>9} {'Gen4_W':>8}"
          f"  {'G3-st':6} {'G4-st':6}  {'O2degC':>6}  notes")
    print(f"  {'-'*6}  {'-'*9} {'-'*8}"
          f"  {'-'*6} {'-'*6}  {'-'*6}  {'-'*22}")

    s0 = _snapshot(0.0, graph, g3, g4, o2, note='post-repropagate')
    snapshots.append(s0)
    print(f"  {s0['t']:6.2f}s  {s0['g3_W']:>9.1f} {s0['g4_W']:>8.1f}"
          f"  {s0['g3_st']:6} {s0['g4_st']:6}  {s0['o2_temp']:>6.1f}  {s0['note']}")

    # ── Simulation loop ───────────────────────────────────────────────────────
    for step in range(1, steps + 1):
        for panel in graph.panels:
            node_cls = NodeRegistry.get(panel['type'])
            if node_cls:
                node_cls.tick(panel, dt, graph)
        graph.update_all_gen_draws()

        if step % sample_every == 0:
            t    = step * dt
            note = ''
            if o2.get('temperature', 0) >= (o2.get('maxTemp', 150) - 2):
                note = 'O2-peak-temp'
            elif o2.get('state') == 'off' and o2.get('temperature', 0) > 0:
                note = 'O2-cooling'

            s = _snapshot(t, graph, g3, g4, o2, note=note)
            snapshots.append(s)
            print(f"  {s['t']:6.2f}s  {s['g3_W']:>9.1f} {s['g4_W']:>8.1f}"
                  f"  {s['g3_st']:6} {s['g4_st']:6}  {s['o2_temp']:>6.1f}  {s['note']}")

    # ── Assertions ────────────────────────────────────────────────────────────
    print("\n  Validating...")

    # 0 blown throughout
    blown_final = [p for p in graph.panels if p.get('state') == 'blown']
    assert len(blown_final) == 0, \
        f"Expected 0 blown, got {len(blown_final)}: {[p['id'] for p in blown_final]}"
    print("  ok  0 blown throughout 15s run")

    # Gen3 and Gen4 stayed on
    assert g3.get('state') == 'on', \
        f"Gen3 (Auxiliary Generator) should be 'on' at end, got '{g3.get('state')}'"
    assert g4.get('state') == 'on', \
        f"Gen4 (Emergency Battery) should be 'on' at end, got '{g4.get('state')}'"
    print("  ok  Gen3 and Gen4 on at t=15s")

    post_snaps = snapshots[1:]
    g3_draws   = [s['g3_W'] for s in post_snaps]
    g4_draws   = [s['g4_W'] for s in post_snaps]
    g3_range   = max(g3_draws) - min(g3_draws)

    # Gen3 draw must vary (ripple + heater thermal cycling)
    assert g3_range >= 50, \
        f"Gen3 draw should vary >=50W from ripple/heater loads, got {g3_range:.1f}W range"
    print(f"  ok  Gen3 draw variation: {g3_range:.1f}W  "
          f"(min={min(g3_draws):.1f}W  max={max(g3_draws):.1f}W)")

    # Gen4 loaded but below rated capacity
    rated_w = g4.get('volts', 120) * g4.get('amps', 8)
    assert all(w > 0 for w in g4_draws), \
        "Gen4 (emergency battery) should carry load throughout"
    assert all(w < rated_w for w in g4_draws), \
        f"Gen4 should stay below rated {rated_w}W, peak was {max(g4_draws):.1f}W"
    print(f"  ok  Gen4 stable load: {min(g4_draws):.1f}--{max(g4_draws):.1f}W  "
          f"(rated {rated_w}W max)")

    # O2 Generator heater is warming up (thermal cycling active)
    max_o2_temp = max(s['o2_temp'] for s in post_snaps)
    assert max_o2_temp > 1.0, \
        f"O2 Generator (#16) temp should rise during 15s run, max={max_o2_temp:.1f}C"
    print(f"  ok  O2 Generator peak temp: {max_o2_temp:.1f}C  "
          f"(heatRate={o2.get('heatRate', '?')} deg/s, "
          f"maxTemp={o2.get('maxTemp', '?')}C)")

    print("\nok  15-second auxiliary-power startup run test passed!")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 76)
    print("Python Power Graph -- 15-Second Auxiliary-Power Startup Run")
    print("=" * 76)

    try:
        test_startup_run_15s()
        print("\n" + "=" * 76)
        print("ok  ALL 1 TEST PASSED!")
        print("=" * 76)
    except AssertionError as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 76)
        sys.exit(1)
