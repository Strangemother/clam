"""
nodes/bus_bar.py
──────────────────────────────────────────────────────────────────────────────
BusBar — weighted proportional power distributor.

States: 'off' | 'distributing'

Takes a single inbound signal and distributes the amperage proportionally
across all outbound pips using a configurable weight per output.

Weights are normalised to sum to 1.0 before distribution, so their absolute
values don't matter — only their relative ratios.

Example: weights=[3, 1, 1] on a 3-output bar with 10A input:
  → out0 = 6A, out1 = 2A, out2 = 2A  (voltage unchanged)

For a single-unit subclass:

    class PowerRail(BusBar):
        type   = 'power-rail'
        label  = 'Power Rail'
        catalog = [
            {'key': 'rail-4', 'label': 'Power Rail 4-way',
             'outputCount': 4, 'weights': [1, 1, 1, 1]},
        ]
    NodeRegistry.register(PowerRail)
"""

from typing import Dict, List
from power_graph.node_base import NodeBase, Signal
from power_graph.node_registry import NodeRegistry


class BusBar(NodeBase):
    """Proportional current distributor."""

    type  = 'bus-bar'
    label = 'Bus Bar'
    group = 'Routing'
    dispatch_delay = 80

    catalog = [
        {'key': 'bus-bar-2', 'label': 'Bus Bar 2-way', 'outputCount': 2, 'weights': [1, 1]},
        {'key': 'bus-bar-4', 'label': 'Bus Bar 4-way', 'outputCount': 4, 'weights': [1, 1, 1, 1]},
        {'key': 'bus-bar-6', 'label': 'Bus Bar 6-way', 'outputCount': 6, 'weights': [1]*6},
        {'key': 'bus-bar-8', 'label': 'Bus Bar 8-way', 'outputCount': 8, 'weights': [1]*8},
    ]

    @classmethod
    def _default_pips_outbound(cls, node_id: int) -> List[Dict]:
        return [
            {'label': f'{node_id}:out0', 'index': 0},
            {'label': f'{node_id}:out1', 'index': 1},
        ]

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        out_count = preset.get('outputCount', 2)
        raw_w     = preset.get('weights', [1] * out_count)
        base = super().defaults(node_id, preset)
        base['pipsOutbound'] = [{'label': f'{node_id}:out{i}', 'index': i}
                                 for i in range(out_count)]
        base.update({
            'outputCount':  out_count,
            'weights':      list(raw_w),
            '_norm_weights': cls._normalise(raw_w),
            'state':        'off',
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'outputCount', 'weights']

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(weights: List[float]) -> List[float]:
        total = sum(weights)
        if total == 0:
            n = len(weights)
            return [1.0 / n] * n
        return [w / total for w in weights]

    # ── Core logic ────────────────────────────────────────────────────────────

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        if signal is None:
            if panel['state'] != 'off':
                cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'off'})
            panel['state'] = 'off'
            for i in range(panel.get('outputCount', 2)):
                graph.emit_pip(panel, i, None)
            return

        nw  = panel.get('_norm_weights', [])
        out = panel.get('outputCount', 2)
        v   = signal.get('v', 0.0)
        a   = signal.get('a', 0.0)

        if panel['state'] != 'distributing':
            cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'distributing'})
        panel['state'] = 'distributing'

        for i in range(out):
            frac    = nw[i] if i < len(nw) else 0.0
            out_sig = {'v': v, 'a': round(a * frac, 4)}
            graph.emit_pip(panel, i, out_sig)

    # ── Actions ───────────────────────────────────────────────────────────────

    @classmethod
    def set_weight(cls, panel: Dict, index: int, value: float, graph):
        """Update a single weight and re-distribute."""
        weights = panel.get('weights', [])
        if 0 <= index < len(weights):
            weights[index]         = max(0.0, value)
            panel['_norm_weights'] = cls._normalise(weights)
            cls.dispatch(panel, 'bus-bar:weights', {'weights': weights})
            # Re-propagate
            sources  = panel.get('powerSources', {})
            combined = graph.combine_sources(sources) if sources else None
            cls.apply(panel, combined, graph)

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev = panel['state']
        panel['state'] = 'off'
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
        for i in range(panel.get('outputCount', 2)):
            graph.emit_pip(panel, i, None)


class PowerRail(BusBar):
    """
    Power Rail — equal-weight bus strip.

    Single-unit class example: subclasses BusBar with a new type/catalog.
    """
    type  = 'power-rail'
    label = 'Power Rail'
    catalog = [
        {'key': 'rail-4', 'label': 'Power Rail 4-way',
         'outputCount': 4, 'weights': [1, 1, 1, 1]},
        {'key': 'rail-8', 'label': 'Power Rail 8-way',
         'outputCount': 8, 'weights': [1]*8},
    ]


NodeRegistry.register(BusBar)
NodeRegistry.register(PowerRail)
