"""
nodes/heater.py
──────────────────────────────────────────────────────────────────────────────
Heater — extends Load with thermal simulation and thermostat.

Extra states: load 'on' / 'off' / 'brownout' / 'blown' states still apply,
but Heater adds a heatState field:

  heatState: 'cold' | 'warming' | 'hot'

Thermostat behaviour
  • temperature rises at heatRate °C/s while powered
  • temperature falls at coolRate °C/s while off / tripped
  • when temperature >= maxTemp  → thermostat cuts power (heatSwitch = False)
  • when temperature <= resetTemp → thermostat restores power (heatSwitch = True)

The effective wattage drawn modulates from minWatts → rated watts as the
element heats up (resistance effect).
"""

import math
from typing import Dict, List
from power_graph.node_base import NodeBase, Signal
from power_graph.node_registry import NodeRegistry
from .load import Load


class Heater(Load):
    """Resistive heater with thermal simulation."""

    type  = 'heater'
    label = 'Heater'
    group = 'Loads'
    dispatch_delay = 200

    catalog = [
        {'key': 'heater-1kw',  'label': 'Heater 1kW',     'watts': 1000, 'heatRate': 2.0, 'coolRate': 0.5, 'maxTemp': 80,  'resetTemp': 60},
        {'key': 'heater-2kw',  'label': 'Heater 2kW',     'watts': 2000, 'heatRate': 3.5, 'coolRate': 0.6, 'maxTemp': 80,  'resetTemp': 60},
        {'key': 'heater-3kw',  'label': 'Heater 3kW',     'watts': 3000, 'heatRate': 5.0, 'coolRate': 0.8, 'maxTemp': 80,  'resetTemp': 60},
        {'key': 'heater-oil',  'label': 'Oil Heater 2kW', 'watts': 2000, 'heatRate': 1.0, 'coolRate': 0.1, 'maxTemp': 75,  'resetTemp': 45},
    ]

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)  # Load.defaults
        base.update({
            'temperature': preset.get('temperature', 20.0),
            'heatState':   'cold',
            'heatSwitch':  True,               # thermostat relay
            'heatRate':    preset.get('heatRate',   2.0),   # °C/s
            'coolRate':    preset.get('coolRate',   0.5),   # °C/s
            'maxTemp':     preset.get('maxTemp',   80.0),
            'resetTemp':   preset.get('resetTemp', 60.0),
            'minWatts':    preset.get('minWatts', preset.get('watts', 1000) * 0.3),
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'heatRate', 'coolRate', 'maxTemp', 'resetTemp']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        # Override effective watts with thermal-adjusted watts before Load.apply()
        if panel.get('heatSwitch') and panel.get('state') == 'on':
            temp  = panel.get('temperature', 20)
            max_t = panel.get('maxTemp', 80)
            frac  = min(1.0, temp / max_t) if max_t > 0 else 1.0
            min_w = panel.get('minWatts', panel.get('watts', 1000) * 0.3)
            panel['watts'] = int(
                min_w + (panel.get('watts', 1000) - min_w) * frac
            )
        elif not panel.get('heatSwitch'):
            # Thermostat tripped — force off signal to Load
            signal = None

        super().apply(panel, signal, graph)

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        super().tick(panel, dt, graph)  # Load.tick handles spike + noise + cap

        temp   = panel.get('temperature', 20.0)
        is_on  = panel.get('state') in ('on', 'brownout')

        if is_on and panel.get('heatSwitch'):
            temp += panel.get('heatRate', 2.0) * dt
        else:
            temp -= panel.get('coolRate', 0.5) * dt
            temp  = max(20.0, temp)   # ambient floor

        panel['temperature'] = round(temp, 2)

        # Thermostat transitions
        hs     = panel.get('heatSwitch', True)
        max_t  = panel.get('maxTemp', 80)
        rst_t  = panel.get('resetTemp', 60)

        if hs and temp >= max_t:
            panel['heatSwitch'] = False
            panel['heatState']  = 'hot'
            cls.dispatch(panel, 'heater:trip', {'temperature': temp})
        elif not hs and temp <= rst_t:
            panel['heatSwitch'] = True
            panel['heatState']  = 'warming'
            cls.dispatch(panel, 'heater:resume', {'temperature': temp})

        # heatState
        if temp < 30:
            panel['heatState'] = 'cold'
        elif panel.get('heatSwitch'):
            panel['heatState'] = 'warming'

        cls.throttle(panel, 'heater:temperature', {'temperature': panel['temperature'],
                                                    'heatState': panel['heatState']})


NodeRegistry.register(Heater)
