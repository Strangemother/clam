"""
nodes/bulb.py
──────────────────────────────────────────────────────────────────────────────
Bulb — resistive sink; no outbound pip.

States: 'off' | 'dim' | 'on' | 'blown'

  off   — no power or below threshold
  dim   — powered but low voltage (voltRatio < 0.9 or ampRatio < 1)
  on    — fully powered
  blown — permanently failed; needs replacement

Blown conditions
  volts > maxVolts (1.2× nominal) OR amps > ratedAmps × 1.5

Brightness model
  dim  → brightness = min(1, voltRatio * min(1, ampRatio)) * 0.55
  on   → brightness = min(1.0, voltRatio)
  off / blown → brightness = 0
"""

import math
from typing import Dict, List
from power_graph.node_base import NodeBase, Signal, NOMINAL_VOLTS, SpikeProfile
from power_graph.node_registry import NodeRegistry


class Bulb(NodeBase):
    """Light bulb — resistive sink."""

    type  = 'bulb'
    label = 'Light'
    group = 'Loads'
    dispatch_delay = 80

    catalog = [
        {'key': 'led-5w',   'label': 'LED 5W',     'watts': 5,   'maxVolts': 264},
        {'key': 'bulb-40w', 'label': 'Bulb 40W',   'watts': 40,  'maxVolts': 288},
        {'key': 'bulb-60w', 'label': 'Bulb 60W',   'watts': 60,  'maxVolts': 288},
        {'key': 'bulb-100w','label': 'Bulb 100W',  'watts': 100, 'maxVolts': 268},
    ]

    @classmethod
    def _default_spike(cls) -> SpikeProfile:
        return SpikeProfile(enabled=True, percent=50, duration=0.2)

    @classmethod
    def _default_pips_outbound(cls, node_id: int) -> List[Dict]:
        return []  # Bulbs are sinks

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        watts    = preset.get('watts', 60)
        # rated amps at nominal volts
        rated_a  = watts / NOMINAL_VOLTS
        base.update({
            'watts':      watts,
            'maxVolts':   preset.get('maxVolts', 288),
            'ratedAmps':  preset.get('ratedAmps', rated_a),
            'minVolts':   preset.get('minVolts', 100),
            'blown':      False,
            'brightness': 0.0,
            'state':      'off',
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'watts', 'maxVolts', 'minVolts']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        if panel.get('blown'):
            if panel['state'] != 'blown':
                panel['state']      = 'blown'
                panel['brightness'] = 0.0
                cls.dispatch(panel, 'bulb:blown', {'id': panel['id']})
            return

        if signal is None or signal.get('v', 0) < panel.get('minVolts', 100):
            if panel['state'] != 'off':
                cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'off'})
            panel['state']      = 'off'
            panel['brightness'] = 0.0
            return

        volts     = signal.get('v', 0)
        amps      = signal.get('a', 0)
        nom_volts = panel.get('maxVolts', 288) / 1.2  # nominal = maxVolts / 1.2

        # ── Blown check (overvoltage only) ────────────────────────────────────
        if volts > panel.get('maxVolts', 288):
            panel['blown']      = True
            panel['state']      = 'blown'
            panel['brightness'] = 0.0
            cls.dispatch(panel, 'bulb:blown', {'volts': volts, 'amps': amps})
            return

        volt_ratio = volts / nom_volts if nom_volts > 0 else 1.0
        amp_ratio  = (amps / panel['ratedAmps']) if panel.get('ratedAmps', 0) > 0 else 1.0
        prev_state = panel['state']

        if volt_ratio < 0.9 or amp_ratio < 0.8:
            panel['state']      = 'dim'
            panel['brightness'] = min(1.0, volt_ratio * min(1.0, amp_ratio)) * 0.55
        else:
            if prev_state == 'off':
                cls.start_spike(panel)
            panel['state']      = 'on'
            panel['brightness'] = min(1.0, volt_ratio)

        if prev_state != panel['state']:
            cls.dispatch(panel, 'state:change', {'from': prev_state, 'to': panel['state']})
        cls.throttle(panel, 'bulb:brightness', {'brightness': round(panel['brightness'], 3)})

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        cls.tick_spike(panel, dt)

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev            = panel['state']
        panel['blown']  = False
        panel['state']  = 'off'
        panel['brightness'] = 0.0
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})


NodeRegistry.register(Bulb)
