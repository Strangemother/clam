"""
nodes/meter.py
──────────────────────────────────────────────────────────────────────────────
Meter — transparent pass-through that samples voltage, amps and watts.

States: 'off' | 'on'

The meter does not modify the signal in any way; it simply records readings
and emits them as throttled events so that dashboards can display live values.
"""

from typing import Dict, List
from power_graph.node_base import NodeBase, Signal
from power_graph.node_registry import NodeRegistry


class Meter(NodeBase):
    """Inline measuring instrument — transparent pass-through."""

    type  = 'meter'
    label = 'Meter'
    group = 'Instrumentation'
    dispatch_delay = 120

    catalog = [
        {'key': 'meter-v',  'label': 'Voltmeter'},
        {'key': 'meter-a',  'label': 'Ammeter'},
        {'key': 'meter-vaw','label': 'Multi-Meter'},
    ]

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        base.update({
            'reading_volts': 0.0,
            'reading_amps':  0.0,
            'reading_watts': 0.0,
            'state':         'off',
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields()]

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        if signal is None:
            if panel['state'] != 'off':
                cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'off'})
            panel.update({'state': 'off', 'reading_volts': 0.0,
                          'reading_amps': 0.0, 'reading_watts': 0.0})
            graph.emit(panel, None)
            return

        v = signal.get('v', 0.0)
        a = signal.get('a', 0.0)
        w = round(v * a, 2)

        changed = (
            panel.get('reading_volts') != v or
            panel.get('reading_amps')  != a
        )

        panel['reading_volts'] = v
        panel['reading_amps']  = a
        panel['reading_watts'] = w

        if panel['state'] != 'on':
            cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'on'})
        panel['state'] = 'on'

        if changed:
            cls.throttle(panel, 'meter:reading', {'v': v, 'a': a, 'w': w})

        # Pass signal through unmodified
        graph.emit(panel, signal)

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev = panel['state']
        panel.update({'state': 'off', 'reading_volts': 0.0,
                      'reading_amps': 0.0, 'reading_watts': 0.0})
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
        graph.emit(panel, None)


NodeRegistry.register(Meter)
