"""
loader.py
──────────────────────────────────────────────────────────────────────────────
Layout loader — builds a PowerGraph from the JSON layout format used by the
func-pipes / pipes-view tools.

Layout JSON format
  {
    "nodes": [
      { "id": 1, "type": "gen", "title": "...", "config": { ... } },
      ...
    ],
    "connections": [
      {
        "sender":   { "label": 1, "direction": "outbound", "pipIndex": 0 },
        "receiver": { "label": 5, "direction": "inbound",  "pipIndex": 0 },
        "line": { "color": "#00e87c", "width": 2 }
      },
      ...
    ],
    "edges": {
      "1-0-5-0": { "enabled": true, "wireType": "copper", "length": 274, ... },
      ...
    }
  }

Usage:
    from power_graph.loader import load_layout
    from power_graph.graph import PowerGraph

    with open('spaceship.json') as f:
        layout = json.load(f)
    graph = PowerGraph()
    load_layout(graph, layout)
    # graph is now live — generators have emitted their initial signals
"""

import json
from pathlib import Path
from typing import Dict, Union


def load_layout(graph, layout: Dict) -> None:
    """
    Populate *graph* from a layout dict.  Modifies graph in-place.

    Existing panels and connections are not cleared — call graph.reset() first
    if you want a clean slate.

    Args:
        graph:  PowerGraph instance
        layout: Parsed layout dict (from JSON)
    """
    nodes       = layout.get('nodes', [])
    connections = layout.get('connections', [])
    edges       = layout.get('edges', {})

    # ── 1. Spawn panels, preserving their JSON ids ────────────────────────────
    id_map: Dict[int, Dict] = {}   # json_id → panel dict

    for node in nodes:
        json_id   = node['id']
        node_type = node.get('type', 'load')
        title     = node.get('title') or node.get('label', '')
        config    = dict(node.get('config') or {})

        # Force the panel to get the ID from the JSON
        graph._next_id = json_id
        panel = graph.spawn(node_type, label=title, preset=config)

        # Some config fields (live, enabled, spike, ripple) may need to be
        # written directly into the panel since spawn/defaults may not copy all.
        for key, val in config.items():
            if key not in ('label',) and key in panel:
                panel[key] = val
            elif key not in panel:
                panel[key] = val

        id_map[json_id] = panel

    # Clear stale runtime state so first propagation rewrites them cleanly.
    # powerSources may have been persisted from a previous live session;
    # those values are meaningless until generators re-emit on startup.
    for panel in graph.panels:
        panel['powerSources'] = {}
        panel['signal'] = None

    # Ensure _next_id is beyond all used ids so future spawns don't collide
    if id_map:
        graph._next_id = max(id_map) + 1

    # ── 2. Wire up connections ────────────────────────────────────────────────
    for conn in connections:
        sender   = conn.get('sender', {})
        receiver = conn.get('receiver', {})

        from_id  = sender.get('label')
        to_id    = receiver.get('label')
        from_pip = sender.get('pipIndex', 0)
        to_pip   = receiver.get('pipIndex', 0)

        if from_id is None or to_id is None:
            continue

        from_panel = id_map.get(from_id)
        to_panel   = id_map.get(to_id)
        if not from_panel or not to_panel:
            continue

        # Look up edge properties from the edges dict
        edge_key = f"{from_id}-{from_pip}-{to_id}-{to_pip}"
        edge_props = edges.get(edge_key, {})
        wire_type  = edge_props.get('wireType', 'copper')
        length     = edge_props.get('length', 0)
        manual_r   = edge_props.get('manualResistance')

        graph.connect(
            from_panel, from_pip,
            to_panel,   to_pip,
            wireType=wire_type,
            length=length,
            manualResistance=manual_r,
        )

    # ── 3. Initial propagation from live generators ───────────────────────────
    for panel in graph.panels:
        if panel.get('type') == 'gen' and panel.get('live'):
            from .nodes.generator import Generator
            Generator.start_spike(panel)
            m = Generator.spike_multiplier(panel)
            graph.emit(panel, {
                'v': round(panel.get('volts', 240) * m, 2),
                'a': round(panel.get('amps',  13)  * m, 3),
            })

    graph.update_all_gen_draws()


def load_layout_file(graph, path: Union[str, Path]) -> None:
    """
    Load a layout JSON file by path and call load_layout().

    Args:
        graph: PowerGraph instance
        path:  Path to .json layout file
    """
    with open(path, 'r', encoding='utf-8') as f:
        layout = json.load(f)
    load_layout(graph, layout)
