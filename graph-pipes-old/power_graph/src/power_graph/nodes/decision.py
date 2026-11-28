"""
nodes/decision.py
──────────────────────────────────────────────────────────────────────────────
Decision — multi-output routing node.

States: 'off' | 'routing' | 'blocked' | 'error'

Override `decide(panel, signal, input_index, graph)` in a subclass to
implement custom routing logic.  The method should return:
  • an int  — single output pip index to receive the signal
  • a list  — multiple output pip indices each receive the signal
  • None    — block all outputs

Default routing: input pip at index N → output pip at index N (1:1).

Per-pip signal cache (`_pip_signals`) allows the node to track what arrived
on each inbound pip for the re-routing tick.

Example subclass:

    class Toggle2Way(Decision):
        type  = 'toggle-2way'
        label = 'Toggle 2-Way'
        catalog = [{'key': 'tog2', 'label': 'Toggle 2-Way',
                    'inputCount': 1, 'outputCount': 2}]

        _side = 0  # class-level for simplicity; use panel dict in practice

        @classmethod
        def decide(cls, panel, signal, input_index, graph):
            cls._side ^= 1
            return cls._side

    NodeRegistry.register(Toggle2Way)
"""

from typing import Dict, List, Optional, Union
from power_graph.node_base import NodeBase, Signal
from power_graph.node_registry import NodeRegistry


class Decision(NodeBase):
    """Multi-output routing node with override-able decision logic."""

    type  = 'decision'
    label = 'Decision'
    group = 'Routing'
    dispatch_delay = 50

    catalog = [
        {'key': 'decision-1-2', 'label': '1→2 Router',  'inputCount': 1, 'outputCount': 2},
        {'key': 'decision-2-2', 'label': '2→2 Router',  'inputCount': 2, 'outputCount': 2},
        {'key': 'decision-1-4', 'label': '1→4 Router',  'inputCount': 1, 'outputCount': 4},
    ]

    @classmethod
    def _default_pips_inbound(cls, node_id: int) -> List[Dict]:
        return [{'label': f'{node_id}:in0', 'index': 0}]

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
        in_count  = preset.get('inputCount', 1)
        out_count = preset.get('outputCount', 2)
        base = super().defaults(node_id, preset)
        base['pipsInbound']  = [{'label': f'{node_id}:in{i}',  'index': i} for i in range(in_count)]
        base['pipsOutbound'] = [{'label': f'{node_id}:out{i}', 'index': i} for i in range(out_count)]
        base.update({
            'inputCount':    in_count,
            'outputCount':   out_count,
            'tickInterval':  preset.get('tickInterval', 0.0),
            'lastDecision':  None,
            '_tick_accum':   0.0,
            '_pip_signals':  {},      # {pip_index: signal}
            'state':         'off',
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'inputCount', 'outputCount', 'tickInterval']

    # ── Override this ─────────────────────────────────────────────────────────

    @classmethod
    def decide(cls, panel: Dict, signal: Signal, input_index: int,
               graph) -> Optional[Union[int, List[int]]]:
        """
        Return the output pip index (or list of indices) to route signal to.
        Return None to block all outputs.

        Default: route to the matching output index.
        """
        out_count = panel.get('outputCount', 2)
        idx       = input_index % out_count
        return idx if idx < out_count else None

    # ── Core logic ────────────────────────────────────────────────────────────

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        # Determine which inbound pip this signal arrived on.
        # Graph passes inbound pip index via panel's last received pip (if tracked).
        # For simplicity we use pip index 0 by default; subclasses override decide().
        in_idx = panel.get('_last_in_pip', 0)
        panel['_pip_signals'][in_idx] = signal

        if signal is None and all(s is None for s in panel['_pip_signals'].values()):
            if panel['state'] != 'off':
                cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'off'})
            panel['state'] = 'off'

        cls._route(panel, signal, in_idx, graph)

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        interval = panel.get('tickInterval', 0.0)
        if not interval:
            return
        panel['_tick_accum'] = panel.get('_tick_accum', 0.0) + dt
        if panel['_tick_accum'] >= interval:
            panel['_tick_accum'] = 0.0
            for in_idx, sig in panel.get('_pip_signals', {}).items():
                cls._route(panel, sig, in_idx, graph)

    @classmethod
    def _route(cls, panel: Dict, signal: Signal, in_idx: int, graph):
        """Apply decide() and emit to chosen output(s)."""
        out_count = panel.get('outputCount', 2)
        result    = cls.decide(panel, signal, in_idx, graph)

        if result is None:
            # Block all
            chosen = []
            new_state = 'blocked'
        elif isinstance(result, int):
            chosen    = [result]
            new_state = 'routing' if signal is not None else 'off'
        else:
            chosen    = list(result)
            new_state = 'routing' if signal is not None else 'off'

        panel['lastDecision'] = chosen

        if panel['state'] != new_state:
            cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': new_state})
        panel['state'] = new_state

        for out_idx in range(out_count):
            out_signal = signal if out_idx in chosen else None
            graph.emit_pip(panel, out_idx, out_signal)

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev = panel['state']
        panel.update({'state': 'off', '_pip_signals': {}, 'lastDecision': None,
                      '_tick_accum': 0.0})
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
        for i in range(panel.get('outputCount', 2)):
            graph.emit_pip(panel, i, None)


NodeRegistry.register(Decision)
