"""
nodes/load.py
──────────────────────────────────────────────────────────────────────────────
Load — scalable power consumer; no outbound pip.

States: 'off' | 'on' | 'brownout' | 'capacitor' | 'blown'

  off        — no signal or below minVolts
  on         — powered normally
  brownout   — below brownout threshold (but above minVolts)
  capacitor  — living off stored charge after supply loss
  blown      — permanently failed due to overvoltage

Capacitor model
  A load may have a capacitance (in Watt-seconds) that lets it survive
  brief power interruptions. When supply is lost, the load drains its charge
  at its rated wattage per second until empty.

Noise model
  Optional sinusoidal wattage fluctuation: ±noise percent at noise interval.
"""

import math
from typing import Dict, List, Optional
from power_graph.node_base import NodeBase, Signal, NOMINAL_VOLTS, SpikeProfile
from power_graph.node_registry import NodeRegistry


class Load(NodeBase):
    """Scalable power consumer."""

    type  = 'load'
    label = 'Load'
    group = 'Loads'
    dispatch_delay = 100
    consumes_watts = True

    catalog = [
        {'key': 'fan',       'label': 'Fan 50W',        'watts': 50,   'capacitanceWs': 0  },
        {'key': 'pump',      'label': 'Pump 250W',       'watts': 250,  'capacitanceWs': 0  },
        {'key': 'motor-sm',  'label': 'Motor 500W',      'watts': 500,  'capacitanceWs': 2  },
        {'key': 'motor-lg',  'label': 'Motor 2kW',       'watts': 2000, 'capacitanceWs': 8  },
        {'key': 'ups-buffer','label': 'UPS Buffer 200W', 'watts': 200,  'capacitanceWs': 30 },
    ]

    @classmethod
    def _default_spike(cls) -> SpikeProfile:
        return SpikeProfile(enabled=True, percent=200, duration=0.5)

    @classmethod
    def _default_pips_outbound(cls, node_id: int) -> List[Dict]:
        return []  # Loads are sinks

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        watts = preset.get('watts', 1000)
        base.update({
            'watts':          watts,
            'minVolts':       preset.get('minVolts',       100),
            'brownoutVolts':  preset.get('brownoutVolts',  180),
            'maxVolts':       preset.get('maxVolts',       280),
            'capacitanceWs':  preset.get('capacitanceWs', 0),
            'chargeWs':       0.0,            # current stored charge
            'noise':          preset.get('noise', 0),        # ±% wattage noise
            'noiseInterval':  preset.get('noiseInterval', 1.0),
            'blown':          False,
            'current_watts':  0.0,
            'state':          'off',
            '_last_signal':   None,
            '_noise_accum':   0.0,
            '_noise_phase':   0.0,
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'watts', 'minVolts', 'brownoutVolts',
                'maxVolts', 'capacitanceWs', 'noise', 'noiseInterval']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        if panel.get('blown'):
            panel['state']         = 'blown'
            panel['current_watts'] = 0.0
            graph.emit(panel, None)
            return

        if signal is not None:
            panel['_last_signal'] = signal

        sig    = signal if signal is not None else panel.get('_last_signal')
        volts  = sig.get('v', 0) if sig else 0
        amps   = sig.get('a', 0) if sig else 0

        # ── Overvoltage blown check ───────────────────────────────────────────
        if sig and volts > panel.get('maxVolts', 280):
            panel['blown']         = True
            panel['state']         = 'blown'
            panel['current_watts'] = 0.0
            cls.dispatch(panel, 'load:blown', {'volts': volts})
            graph.emit(panel, None)
            return

        min_v     = panel.get('minVolts', 100)
        bro_v     = panel.get('brownoutVolts', 180)
        rated_w   = panel.get('watts', 1000)
        cap_ws    = panel.get('capacitanceWs', 0)
        charge    = panel.get('chargeWs', 0.0)
        prev      = panel['state']

        # No signal at all
        if signal is None and not cap_ws:
            panel['state']         = 'off'
            panel['current_watts'] = 0.0
            panel['_last_signal']  = None
            if prev != 'off':
                cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
            graph.emit(panel, None)
            return

        if signal is None and cap_ws:
            # Run on capacitor charge — tick() handles drain
            if charge > 0:
                if panel['state'] != 'capacitor':
                    panel['state'] = 'capacitor'
                    cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'capacitor'})
                return
            else:
                panel['state']         = 'off'
                panel['current_watts'] = 0.0
                if prev != 'off':
                    cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
                graph.emit(panel, None)
                return

        # We have a live signal
        if volts < min_v:
            panel['state']         = 'off'
            panel['current_watts'] = 0.0
            if prev != 'off':
                cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
            graph.emit(panel, None)
            return

        if volts < bro_v:
            panel['state']         = 'brownout'
            panel['current_watts'] = rated_w * (volts / bro_v)
            if prev != 'brownout':
                cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'brownout'})
        else:
            # Full power — apply inrush spike
            if prev in ('off', 'capacitor', 'brownout'):
                cls.start_spike(panel)
            panel['state'] = 'on'
            spike_m        = cls.spike_multiplier(panel)
            panel['current_watts'] = rated_w * spike_m

            # Charge capacitor fully when powered normally
            if cap_ws:
                panel['chargeWs'] = cap_ws

            if prev != 'on':
                cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'on'})

        cls.throttle(panel, 'load:watts', {'watts': round(panel['current_watts'], 1)})
        graph.emit(panel, None)

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        cls.tick_spike(panel, dt)

        # ── Noise oscillation ─────────────────────────────────────────────────
        noise_cfg = panel.get('noise', 0)
        if isinstance(noise_cfg, dict):
            noise_enabled  = noise_cfg.get('enabled', False)
            noise          = noise_cfg.get('amount', 0) if noise_enabled else 0
            noise_interval = noise_cfg.get('period', 1.0)
        else:
            noise          = noise_cfg
            noise_interval = panel.get('noiseInterval', 1.0)

        if noise and panel['state'] == 'on':
            panel['_noise_phase'] = (
                panel.get('_noise_phase', 0.0) +
                dt * 2 * math.pi / max(0.01, noise_interval)
            )
            offset = math.sin(panel['_noise_phase']) * noise / 100
            panel['current_watts'] = panel.get('watts', 1000) * (1.0 + offset) * cls.spike_multiplier(panel)

        # ── Capacitor drain ───────────────────────────────────────────────────
        if panel['state'] == 'capacitor':
            drain            = panel.get('current_watts', panel.get('watts', 1000))
            panel['chargeWs'] = max(0.0, panel.get('chargeWs', 0.0) - drain * dt)
            if panel['chargeWs'] <= 0:
                panel['state']         = 'off'
                panel['current_watts'] = 0.0
                cls.dispatch(panel, 'state:change', {'from': 'capacitor', 'to': 'off'})

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev                   = panel['state']
        panel['blown']         = False
        panel['state']         = 'off'
        panel['current_watts'] = 0.0
        panel['chargeWs']      = 0.0
        panel['_last_signal']  = None
        panel['powerSources']  = {}
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'off'})
        graph.emit(panel, None)


NodeRegistry.register(Load)
