"""
nodes/series_battery.py
──────────────────────────────────────────────────────────────────────────────
SeriesBattery — rechargeable battery in a series circuit.

States: 'off' | 'charging' | 'discharging' | 'full' | 'dead' | 'pass'

  pass        — passthrough only, no stored charge (chargeAmps = 0 or cap = 0)
  charging    — receiving power, storing energy
  discharging — providing own EMF contribution when downstream draws current
  full        — at capacity; stops charging
  dead        — charge exhausted; no contribution
  off         — no inbound signal and dead/empty

Energy model
  chargeInW  = min(inAmps, chargeAmps) * volts          (watts into battery)
  chargeOutW = drawWatts * (volts / totalV)              (battery share)
  chargeWh   += chargeInW  * dt / 3600                  (per tick)
  chargeWh   -= chargeOutW * dt / 3600                  (per tick, when discharging)

The battery stacks its own EMF onto the inbound signal voltage so series
batteries increase total line voltage.
"""

from typing import Dict, List
from power_graph.node_base import NodeBase, Signal
from power_graph.node_registry import NodeRegistry


class SeriesBattery(NodeBase):
    """Rechargeable series-circuit battery."""

    type  = 'series-battery'
    label = 'Battery'
    group = 'Storage'
    dispatch_delay = 200

    @classmethod
    def _default_ripple(cls):
        # Internal resistance variation under charge/discharge cycles
        return RippleProfile(enabled=True, amount=0.6, interval=1.2)

    catalog = [
        {'key': 'series-12v',    'label': 'Lead-Acid 12V 7Ah',  'volts': 12,  'amps': 7,   'chargeAmps': 2,  'capacityWh': 84 },
        {'key': 'series-24v',    'label': 'Lead-Acid 24V 7Ah',  'volts': 24,  'amps': 7,   'chargeAmps': 3,  'capacityWh': 168},
        {'key': 'series-48v',    'label': 'LiFePO4 48V 10Ah',   'volts': 48,  'amps': 10,  'chargeAmps': 5,  'capacityWh': 480},
        {'key': 'series-lipo',   'label': 'LiPo 11.1V 5Ah',     'volts': 11.1,'amps': 5,   'chargeAmps': 3,  'capacityWh': 55.5},
        {'key': 'series-9v',     'label': '9V Block',            'volts': 9,   'amps': 0.6, 'chargeAmps': 0,  'capacityWh': 5.4},
        {'key': 'series-super',  'label': 'Supercapacitor 2.7V', 'volts': 2.7, 'amps': 50,  'chargeAmps': 50, 'capacityWh': 0.05},
    ]

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        cap_wh = preset.get('capacityWh', 84)
        base.update({
            'volts':          preset.get('volts',      12),
            'amps':           preset.get('amps',       7),
            'chargeAmps':     preset.get('chargeAmps', 2),
            'capacityWh':     cap_wh,
            'chargeWh':       preset.get('chargeWh', cap_wh * 0.8),  # start at 80%
            'chargePercent':  80.0,
            'drawWatts':      0.0,
            'chargeInW':      0.0,
            'chargeOutW':     0.0,
            'inVolts':        0.0,
            'inAmps':         0.0,
            'live':           False,
            'running':        True,   # internal on/off switch (toggled by user)
            'state':          'off',
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'volts', 'amps', 'chargeAmps', 'capacityWh']

    @classmethod
    def toggle(cls, panel: Dict, graph):
        """Internal on/off switch — independent of graph enabled state."""
        panel['running'] = not panel.get('running', True)
        prev = panel['state']
        if not panel['running']:
            panel['live']  = False
            panel['state'] = 'off'
            cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
            graph.emit(panel, None)
        else:
            # Re-apply with current sources so battery resumes immediately
            sources  = panel.get('powerSources', {})
            combined = graph.combine_sources(sources) if sources else None
            cls.apply(panel, combined, graph)

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        # Internal switch off — cut output regardless of incoming signal
        if not panel.get('running', True):
            graph.emit(panel, None)
            return

        cap_wh     = panel.get('capacityWh', 84)
        charge_amp = panel.get('chargeAmps', 2)

        if signal is None:
            # No external power — discharge or go off
            panel['inVolts'] = 0.0
            panel['inAmps']  = 0.0
            panel['live']    = False
            if panel.get('chargeWh', 0) > 0 and cap_wh > 0:
                panel['state'] = 'discharging'
                # Emit own EMF as primary source
                graph.emit(panel, {'v': panel.get('volts', 12), 'a': panel.get('amps', 7)})
            else:
                if panel['state'] != 'off':
                    cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'off'})
                panel['state'] = 'off'
                graph.emit(panel, None)
            return

        v_in  = signal.get('v', 0.0)
        a_in  = signal.get('a', 0.0)
        b_v   = panel.get('volts', 12)
        b_a   = panel.get('amps', 7)
        panel['inVolts'] = v_in
        panel['inAmps']  = a_in
        panel['live']    = True

        # Charge contribution
        charge_wh = panel.get('chargeWh', 0.0)

        if not cap_wh or not charge_amp:
            # Passthrough battery
            if panel['state'] != 'pass':
                cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'pass'})
            panel['state']     = 'pass'
            panel['chargeInW'] = 0.0
            graph.emit(panel, {'v': v_in + b_v, 'a': a_in})
            return

        charge_in_w = min(a_in, charge_amp) * b_v
        panel['chargeInW'] = charge_in_w

        if charge_wh >= cap_wh:
            new_state = 'full'
        elif charge_wh <= 0:
            new_state = 'dead'
        elif charge_in_w > 0:
            new_state = 'charging'
        else:
            new_state = 'discharging'

        if panel['state'] != new_state:
            cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': new_state})
        panel['state'] = new_state

        cls.throttle(panel, 'battery:charge',
                     {'chargePercent': round(panel.get('chargePercent', 0), 1),
                      'chargeWh': round(charge_wh, 3)})

        # Stack battery EMF on top of inbound voltage
        v_out = v_in + b_v
        graph.emit(panel, {'v': round(v_out, 2), 'a': a_in})

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        cap_wh    = panel.get('capacityWh', 0)
        charge_wh = panel.get('chargeWh', 0.0)
        if not cap_wh:
            return

        in_w   = panel.get('chargeInW', 0.0)
        draw_w = panel.get('drawWatts', 0.0)
        b_v    = panel.get('volts', 12)
        total_v = panel.get('inVolts', b_v) + b_v
        out_w   = draw_w * (b_v / total_v) if total_v > 0 else 0.0

        panel['chargeOutW'] = out_w
        delta_wh = (in_w - out_w) * dt / 3600.0
        charge_wh = max(0.0, min(cap_wh, charge_wh + delta_wh))
        panel['chargeWh']      = charge_wh
        panel['chargePercent'] = (charge_wh / cap_wh * 100) if cap_wh else 0

        # Dead / revive transitions
        state = panel['state']
        if state == 'discharging' and charge_wh <= 0:
            panel['state'] = 'dead'
            cls.dispatch(panel, 'battery:dead', {})
            graph.emit(panel, None)
        elif state == 'dead' and in_w > 0 and charge_wh > 0:
            panel['state'] = 'charging'
            cls.dispatch(panel, 'battery:revived', {})

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev               = panel['state']
        cap_wh             = panel.get('capacityWh', 84)
        panel['chargeWh']  = cap_wh * 0.8
        panel['state']     = 'off'
        panel['live']      = False
        panel['running']   = True
        panel['chargeInW'] = 0.0
        panel['chargeOutW'] = 0.0
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
        graph.emit(panel, None)


NodeRegistry.register(SeriesBattery)
