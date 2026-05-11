"""
nodes/converter.py
──────────────────────────────────────────────────────────────────────────────
Converter — step-up / step-down transformer / power supply.

States: 'off' | 'step-up' | 'step-down' | 'unity' | 'fault'

Physics model
  turns_ratio = outVolts / _baseInVolts   (set on first live signal)
  P_out       = P_in * efficiency
  V_out       = V_in * turns_ratio
  A_out       = P_out / V_out

  If V_out would exceed maxOutVolts ('fault'), output is cut.

The dial_up() / dial_down() actions change outVolts by one step and
re-propagate through the graph.
"""

from typing import Dict, List
from power_graph.node_base import NodeBase, Signal
from power_graph.node_registry import NodeRegistry


_VOLT_STEPS = [5, 12, 24, 48, 120, 240, 480]


class Converter(NodeBase):
    """Step-up / step-down power converter."""

    type  = 'converter'
    label = 'Converter'
    group = 'Power'
    dispatch_delay = 150

    catalog = [
        {'key': 'conv-480v', 'label': 'Step-Up 480V',  'outVolts': 480, 'efficiency': 0.92},
        {'key': 'conv-240v', 'label': 'Unity 240V',    'outVolts': 240, 'efficiency': 0.98},
        {'key': 'conv-24v',  'label': 'PSU 24V',       'outVolts': 24,  'efficiency': 0.88},
        {'key': 'conv-12v',  'label': 'PSU 12V',       'outVolts': 12,  'efficiency': 0.85},
        {'key': 'conv-5v',   'label': 'PSU 5V',        'outVolts': 5,   'efficiency': 0.82},
    ]

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        base.update({
            'outVolts':     preset.get('outVolts', 240),
            'efficiency':   preset.get('efficiency', 0.90),
            'maxOutVolts':  preset.get('maxOutVolts', 600),
            # Live readings
            'inVolts':      0.0,
            'inAmps':       0.0,
            'outAmps':      0.0,
            'ratio':        1.0,
            # Snapshot of input voltage when first energised (used as turns base)
            '_baseInVolts': None,
            'state':        'off',
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'outVolts', 'efficiency', 'maxOutVolts']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        if signal is None:
            if panel['state'] != 'off':
                cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'off'})
            panel.update({
                'state': 'off', 'inVolts': 0.0, 'inAmps': 0.0,
                'outAmps': 0.0, 'ratio': 1.0, '_baseInVolts': None,
            })
            graph.emit(panel, None)
            return

        v_in      = signal.get('v', 0.0)
        a_in      = signal.get('a', 0.0)
        out_volts = panel.get('outVolts', 240)
        eff       = panel.get('efficiency', 0.90)

        # Snapshot input volts on first energising
        if panel.get('_baseInVolts') is None:
            panel['_baseInVolts'] = v_in if v_in > 0 else 1.0

        base_in  = panel['_baseInVolts']
        ratio    = out_volts / base_in
        v_out    = v_in * ratio
        p_in     = v_in * a_in
        p_out    = p_in * eff
        a_out    = (p_out / v_out) if v_out > 0 else 0.0

        panel['inVolts']  = v_in
        panel['inAmps']   = a_in
        panel['outAmps']  = a_out
        panel['ratio']    = round(ratio, 3)

        # Fault check
        if v_out > panel.get('maxOutVolts', 600):
            if panel['state'] != 'fault':
                cls.dispatch(panel, 'converter:fault', {'v_out': v_out})
            panel['state'] = 'fault'
            graph.emit(panel, None)
            return

        # Categorise state
        if abs(ratio - 1.0) < 0.02:
            new_state = 'unity'
        elif ratio > 1.0:
            new_state = 'step-up'
        else:
            new_state = 'step-down'

        if panel['state'] != new_state:
            cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': new_state})
        panel['state'] = new_state

        cls.throttle(panel, 'converter:reading',
                     {'ratio': panel['ratio'], 'v_out': round(v_out, 2), 'a_out': round(a_out, 3)})
        graph.emit(panel, {'v': round(v_out, 2), 'a': round(a_out, 3)})

    # ── Actions ───────────────────────────────────────────────────────────────

    @classmethod
    def dial_up(cls, panel: Dict, graph):
        """Increase outVolts to the next step in the standard volt ladder."""
        cur = panel.get('outVolts', 240)
        for v in _VOLT_STEPS:
            if v > cur:
                panel['outVolts']    = v
                panel['_baseInVolts'] = None  # reset turns snapshot
                cls.dispatch(panel, 'converter:dial', {'outVolts': v})
                cls._reprop(panel, graph)
                return

    @classmethod
    def dial_down(cls, panel: Dict, graph):
        """Decrease outVolts to the previous step in the voltage ladder."""
        cur = panel.get('outVolts', 240)
        for v in reversed(_VOLT_STEPS):
            if v < cur:
                panel['outVolts']    = v
                panel['_baseInVolts'] = None
                cls.dispatch(panel, 'converter:dial', {'outVolts': v})
                cls._reprop(panel, graph)
                return

    @classmethod
    def _reprop(cls, panel: Dict, graph):
        """Re-run apply() from cached sources after dial change."""
        sources  = panel.get('powerSources', {})
        combined = graph.combine_sources(sources) if sources else None
        cls.apply(panel, combined, graph)

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev = panel['state']
        panel.update({'state': 'off', 'inVolts': 0.0, 'inAmps': 0.0,
                      'outAmps': 0.0, '_baseInVolts': None})
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
        graph.emit(panel, None)


NodeRegistry.register(Converter)
