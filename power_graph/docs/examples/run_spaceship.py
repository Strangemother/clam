"""
run_spaceship.py
────────────────────────────────────────────────────────────────────────────
Loads func-pipes/layouts/spaceship.json and runs a short simulation.

Run from the workspace root:
    python power_graph/docs/examples/run_spaceship.py

or from within power_graph/:
    python docs/examples/run_spaceship.py
"""

import sys
import json
import time
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parents[3]   # /workspaces/clam
_SRC  = _REPO / 'power_graph' / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from power_graph.graph import PowerGraph
from power_graph.loader import load_layout_file
from power_graph.event_system import EventMonitor

# ── Layout path ───────────────────────────────────────────────────────────────
LAYOUT_PATH = _REPO / 'func-pipes' / 'layouts' / 'spaceship.json'

# ── Boot ──────────────────────────────────────────────────────────────────────
print("=" * 70)
print("SPACESHIP POWER GRAPH — simulation")
print("=" * 70)

graph = PowerGraph()

# Attach a simple event printer (only key events)
TRACKED = {
    'state:change', 'gen:tripped', 'gen:sag', 'bulb:blown',
    'load:blown', 'breaker:tripped', 'console:ready', 'console:booting',
    'heater:trip', 'battery:dead', 'converter:fault',
}

events_seen = []

def on_any(event_type, label, data):
    if event_type in TRACKED:
        events_seen.append((event_type, label, data))

graph.emitter.on('*', on_any)


print(f"\nLoading layout: {LAYOUT_PATH.name}")
load_layout_file(graph, LAYOUT_PATH)
print(f"Spawned {len(graph.panels)} panels\n")

# ── Synchronous tick loop (5 simulated seconds at 20 fps) ────────────────────
SIM_SECONDS = 5.0
DT          = 0.05     # 20 fps
steps       = int(SIM_SECONDS / DT)

print(f"Running {SIM_SECONDS}s simulation ({steps} ticks @ {1/DT:.0f} fps)…\n")

t0 = time.time()
for step in range(steps):
    sim_t = step * DT
    for panel in graph.panels:
        from power_graph.node_registry import NodeRegistry
        node_cls = NodeRegistry.get(panel['type'])
        if node_cls:
            node_cls.tick(panel, DT, graph)
    graph.update_all_gen_draws()

wall = time.time() - t0
print(f"Done in {wall*1000:.1f}ms wall-clock\n")

# ── Events collected ──────────────────────────────────────────────────────────
if events_seen:
    print("── Notable events ──────────────────────────────────────────────────")
    for ev_type, label, data in events_seen:
        print(f"  [{ev_type}]  {label}  {data}")
    print()

# ── Final state summary ───────────────────────────────────────────────────────
print("── Final panel states ──────────────────────────────────────────────")

state_counts: dict[str, int] = {}
for panel in graph.panels:
    state = panel.get('state', '?')
    state_counts[state] = state_counts.get(state, 0) + 1

    node_type = panel.get('type', '?')
    label     = panel.get('label', f"panel-{panel['id']}")
    extra = ''

    if node_type == 'gen':
        extra = (f"  {panel.get('volts')}V/{panel.get('amps')}A"
                 f"  draw={panel.get('drawWatts', 0):.0f}W/{panel.get('drawAmps', 0):.2f}A")
    elif node_type == 'bulb':
        extra = f"  brightness={panel.get('brightness', 0):.2f}"
    elif node_type in ('load', 'heater', 'console'):
        extra = f"  watts={panel.get('current_watts', 0):.0f}W"
    elif node_type == 'meter':
        extra = f"  {panel.get('reading_volts', 0):.1f}V  {panel.get('reading_amps', 0):.2f}A"
    elif node_type == 'converter':
        extra = f"  ratio={panel.get('ratio', 1):.3f}  out={panel.get('outVolts', 0)}V"
    elif node_type == 'series-battery':
        extra = f"  {panel.get('chargePercent', 0):.1f}%"

    status = f"[{state:12}]"
    print(f"  {status}  #{panel['id']:2}  {node_type:12}  {label}{extra}")

print()
print("── State summary ───────────────────────────────────────────────────")
for state, count in sorted(state_counts.items()):
    print(f"  {state:12} × {count}")

print()
print("=" * 70)
