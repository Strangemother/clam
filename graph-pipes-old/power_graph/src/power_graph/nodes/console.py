"""
nodes/console.py
──────────────────────────────────────────────────────────────────────────────
ConsoleNode — extends Load with a boot/shutdown state machine.

bootState: 'off' | 'booting' | 'ready' | 'shutdown'

Boot behaviour
  • power applied → 'booting'; bootProgress counts from 0 → 100 over bootDuration
  • bootProgress reaches 100 → 'ready'
  • power removed while 'ready' → 'shutdown'; counts down over shutdownDuration
  • 'shutdown' complete → 'off'

Wattage model
  booting  : rated watts (high initial draw)
  ready    : oscillates between 30 % and 60 % of rated watts (idle load)
  shutdown : reduces linearly to 0 over shutdown period
"""

import math
from typing import Dict, List
from power_graph.node_base import Signal, SpikeProfile
from power_graph.node_registry import NodeRegistry
from .load import Load


class ConsoleNode(Load):
    """Computer / server console with boot state machine."""

    type  = 'console'
    label = 'Console'
    group = 'Loads'
    dispatch_delay = 150

    catalog = [
        {'key': 'console-sm',  'label': 'PC 200W',         'watts': 200,  'bootDuration': 30, 'shutdownDuration': 10},
        {'key': 'console-lg',  'label': 'Workstation 600W','watts': 600,  'bootDuration': 45, 'shutdownDuration': 15},
        {'key': 'server-rack', 'label': 'Server Rack 2kW', 'watts': 2000, 'bootDuration': 60, 'shutdownDuration': 20},
        {'key': 'workstation', 'label': 'Workstation 800W','watts': 800,  'bootDuration': 40, 'shutdownDuration': 12},
    ]

    @classmethod
    def _default_spike(cls) -> SpikeProfile:
        return SpikeProfile(enabled=True, percent=120, duration=1.5)

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        base.update({
            'bootState':       'off',
            'bootProgress':    0.0,
            'bootDuration':    preset.get('bootDuration', 30),
            'shutdownDuration':preset.get('shutdownDuration', 10),
            '_effective_watts':preset.get('watts', 200),
            '_load_accum':     0.0,
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'bootDuration', 'shutdownDuration']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        boot = panel.get('bootState', 'off')

        if signal is None:
            # Lost power
            if boot == 'ready':
                panel['bootState'] = 'shutdown'
                cls.dispatch(panel, 'console:shutdown', {})
            elif boot in ('booting',):
                panel['bootState']    = 'off'
                panel['bootProgress'] = 0.0
                cls.dispatch(panel, 'console:aborted', {})
            # Let Load.apply handle the off state
            panel['current_watts'] = panel.get('_effective_watts', panel.get('watts', 200))
            super().apply(panel, signal, graph)
            return

        if boot == 'off':
            panel['bootState']    = 'booting'
            panel['bootProgress'] = 0.0
            cls.dispatch(panel, 'console:booting', {})

        # Let Load see the effective watts
        panel['watts'] = panel.get('_effective_watts', panel.get('watts', 200))
        super().apply(panel, signal, graph)

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        super().tick(panel, dt, graph)

        boot        = panel.get('bootState', 'off')
        boot_dur    = max(0.01, panel.get('bootDuration', 30))
        shut_dur    = max(0.01, panel.get('shutdownDuration', 10))
        rated_w     = panel.get('watts', 200)

        if boot == 'booting':
            panel['bootProgress'] = min(100.0, panel['bootProgress'] + (dt / boot_dur) * 100)
            panel['_effective_watts'] = rated_w  # full draw during boot
            if panel['bootProgress'] >= 100.0:
                panel['bootState'] = 'ready'
                panel['_load_accum'] = 0.0
                cls.dispatch(panel, 'console:ready', {})

        elif boot == 'ready':
            # Oscillate idle wattage 30%→60% of rated
            panel['_load_accum'] = panel.get('_load_accum', 0.0) + dt
            idle_frac  = 0.45 + 0.15 * math.sin(panel['_load_accum'] * 0.5)
            panel['_effective_watts'] = rated_w * idle_frac
            cls.throttle(panel, 'console:idle', {'watts': round(panel['_effective_watts'], 1)})

        elif boot == 'shutdown':
            panel['bootProgress'] = max(0.0, panel.get('bootProgress', 100) - (dt / shut_dur) * 100)
            frac = panel['bootProgress'] / 100.0
            panel['_effective_watts'] = rated_w * frac * 0.4
            if panel['bootProgress'] <= 0:
                panel['bootState']    = 'off'
                panel['bootProgress'] = 0.0
                cls.dispatch(panel, 'console:off', {})

        cls.throttle(panel, 'console:progress', {
            'bootState': panel['bootState'], 'progress': round(panel.get('bootProgress', 0), 1)
        })

    @classmethod
    def reset(cls, panel: Dict, graph):
        super().reset(panel, graph)
        panel['bootState']        = 'off'
        panel['bootProgress']     = 0.0
        panel['_effective_watts'] = panel.get('watts', 200)


NodeRegistry.register(ConsoleNode)
