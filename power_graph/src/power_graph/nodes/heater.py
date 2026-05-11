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
        {'key': 'heater-1kw',  'label': 'Heater 1kW',     'watts': 1000, 'minWatts':  50, 'noise': 10, 'noiseInterval': 0.4, 'heatRate': 2.0, 'coolRate': 0.5, 'maxTemp': 80,  'resetTemp': 60},
        {'key': 'heater-2kw',  'label': 'Heater 2kW',     'watts': 2000, 'minWatts': 100, 'noise': 10, 'noiseInterval': 0.4, 'heatRate': 3.5, 'coolRate': 0.6, 'maxTemp': 80,  'resetTemp': 60},
        {'key': 'heater-3kw',  'label': 'Heater 3kW',     'watts': 3000, 'minWatts': 150, 'noise': 10, 'noiseInterval': 0.4, 'heatRate': 5.0, 'coolRate': 0.8, 'maxTemp': 80,  'resetTemp': 60},
        {'key': 'heater-oil',  'label': 'Oil Heater 2kW', 'watts': 2000, 'minWatts': 100, 'noise':  6, 'noiseInterval': 0.8, 'heatRate': 1.0, 'coolRate': 0.1, 'maxTemp': 75,  'resetTemp': 45},
    ]

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)  # Load.defaults
        rated  = preset.get('watts', 1000)
        min_w  = preset.get('minWatts', rated * 0.05)   # ~5 % standby draw
        base.update({
            'temperature':         preset.get('temperature', 20.0),
            'heatState':           'cold',
            'heatSwitch':          True,               # thermostat relay
            'heatRate':            preset.get('heatRate',   2.0),   # °C/s
            'coolRate':            preset.get('coolRate',   0.5),   # °C/s
            'maxTemp':             preset.get('maxTemp',   80.0),
            'resetTemp':           preset.get('resetTemp', 60.0),
            'minWatts':            min_w,
            # currentWatts tracks the live scaled draw (minWatts → rated watts)
            # and is the value actually passed to Load.apply — panel['watts']
            # is NEVER modified so the rated ceiling is always preserved.
            'currentWatts':        min_w,
            '_last_emitted_watts': -1.0,
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'heatRate', 'coolRate', 'maxTemp', 'resetTemp']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        rated          = panel['watts']
        min_w          = panel.get('minWatts', rated * 0.05)

        if not panel.get('heatSwitch'):
            # Thermostat tripped — element is off but standby draw remains.
            panel['watts'] = min_w
        else:
            panel['watts'] = panel.get('currentWatts', min_w)

        super().apply(panel, signal, graph)
        panel['watts'] = rated   # always restore the rated ceiling

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
        hs    = panel.get('heatSwitch', True)
        max_t = panel.get('maxTemp', 80)
        rst_t = panel.get('resetTemp', 60)

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

        # ── Dynamic draw: scale currentWatts from minWatts → rated watts ──────
        rated = panel['watts']           # never mutated — always the catalog value
        min_w = panel.get('minWatts', rated * 0.05)

        if panel.get('heatSwitch'):
            # Fraction is relative to the operating band (resetTemp → maxTemp) so
            # draw starts at minWatts when the thermostat re-enables and only
            # reaches rated watts at maxTemp — not at 75% on the very first tick.
            band      = max(1.0, max_t - rst_t)
            heat_frac = min(1.0, max(0.0, (temp - rst_t) / band))
            target    = min_w + (rated - min_w) * heat_frac
        else:
            target = min_w

        # Apply noise ripple directly to the thermal-scaled draw.
        # Load.tick() (called above via super()) already advanced _noise_phase,
        # so we just read it here — no extra state needed.
        noise_cfg = panel.get('noise', 0)
        if isinstance(noise_cfg, dict):
            noise_pct = noise_cfg.get('amount', 0) if noise_cfg.get('enabled') else 0
        else:
            noise_pct = noise_cfg
        if noise_pct and panel.get('state') == 'on':
            offset = math.sin(panel.get('_noise_phase', 0.0)) * noise_pct / 100
            target = max(min_w, target * (1.0 + offset))

        panel['currentWatts'] = round(target, 1)

        # Always keep current_watts in sync — the generator BFS reads this field
        # directly to calculate drawWatts.  Without this, Load.tick() (called via
        # super() above) overwrites current_watts with rated * noise and the
        # generator sees full draw even while the thermostat is tripped.
        panel['current_watts'] = panel['currentWatts']

        # Re-apply whenever the draw shifts (lower threshold so every noisy
        # tick propagates upstream and the generator sees the ripple).
        prev = panel.get('_last_emitted_watts', -1.0)
        if (abs(panel['currentWatts'] - prev) > 0.5
                and panel['state'] in ('on', 'brownout')
                and panel.get('_last_signal') is not None):
            panel['_last_emitted_watts'] = panel['currentWatts']
            cls.apply(panel, panel['_last_signal'], graph)


NodeRegistry.register(Heater)
