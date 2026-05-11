"""
nodes/generator.py
──────────────────────────────────────────────────────────────────────────────
Generator — power source node.

Produces {v, a} when live=True. No inbound pip.

States: 'off' | 'on' | 'sag' | 'tripped'

Overload model (proportion of rated amps)
  ≤ 1.0   — nominal — full rated signal
  1.0–1.3 — sag     — voltage reduced to 85%
  > 1.3   — tripped — output cut, must be manually reset via toggle()

For single-unit variants, extend and set a new type:

    class ShipReactor(Generator):
        type    = 'ship-reactor'
        label   = 'Ship Reactor'
        catalog = [{'key': 'reactor', 'label': 'Ship Reactor', 'volts': 480, 'amps': 120}]

    NodeRegistry.register(ShipReactor)
"""

from typing import Dict, List

from power_graph.node_base import NodeBase, Signal, SpikeProfile, RippleProfile
from power_graph.node_registry import NodeRegistry


class Generator(NodeBase):
    """AC/DC power source."""

    type  = 'gen'
    label = 'Generator'
    group = 'Source'
    dispatch_delay = 200

    catalog = [
        {'key': 'wall-outlet',  'label': 'Wall Outlet',  'volts': 240, 'amps': 13 },
        {'key': 'gen-30a',      'label': 'Generator',    'volts': 240, 'amps': 30 },
        {'key': 'ship-reactor', 'label': 'Ship Reactor', 'volts': 240, 'amps': 120},
        {'key': 'battery-12v',  'label': 'Battery 12V',  'volts': 12,  'amps': 20 },
        {'key': 'battery-48v',  'label': 'Battery 48V',  'volts': 48,  'amps': 30 },
    ]

    @classmethod
    def _default_spike(cls):
        return SpikeProfile(enabled=True, percent=15, duration=0.94)

    @classmethod
    def _default_ripple(cls):
        return RippleProfile(enabled=False, amount=2.0, interval=0.8)

    @classmethod
    def _default_pips_inbound(cls, node_id):
        return []  # generators are sources only

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        base.update({
            'volts':               preset.get('volts', 240),
            'amps':                preset.get('amps',  13),
            'live':                False,
            'overload':            False,
            'drawWatts':           0,
            'drawAmps':            0,
            '_last_emitted_state': None,
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'volts', 'amps', 'live', 'ripple', 'spike']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        """Generators are sources — they do not process inbound signals."""

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        """Decay inrush spike and re-emit the adjusted output signal."""
        was_nonzero  = (panel.get('_spike_timer', 0) > 0)
        still_active = cls.tick_spike(panel, dt)
        if not still_active and not was_nonzero:
            return
        if not panel.get('live') or panel.get('state') in ('tripped', 'off'):
            return
        m = cls.spike_multiplier(panel)
        graph.emit(panel, {
            'v': round(panel.get('volts', 240) * m, 2),
            'a': round(panel.get('amps',  13)  * m, 3),
        })

    # ── Actions ───────────────────────────────────────────────────────────────

    @classmethod
    def toggle(cls, panel: Dict, graph):
        """Toggle on/off. A tripped generator resets to 'off' on first call."""
        if panel.get('state') == 'tripped':
            panel['overload'] = False
            panel['live']     = False
            panel['state']    = 'off'
            cls.dispatch(panel, 'state:change', {'from': 'tripped', 'to': 'off'})
            graph.emit(panel, None)
            graph.update_all_gen_draws()
            return

        prev          = panel.get('state', 'off')
        panel['live'] = not panel.get('live', False)
        panel['state'] = 'on' if panel['live'] else 'off'
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': panel['state']})

        if panel['live']:
            cls.start_spike(panel)
            m = cls.spike_multiplier(panel)
            cls.dispatch(panel, 'gen:start', {'volts': panel.get('volts'), 'amps': panel.get('amps')})
            graph.emit(panel, {
                'v': round(panel.get('volts', 240) * m, 2),
                'a': round(panel.get('amps',  13)  * m, 3),
            })
        else:
            cls.dispatch(panel, 'gen:stop', {'volts': panel.get('volts'), 'amps': panel.get('amps')})
            graph.emit(panel, None)

        graph.update_all_gen_draws()

    @classmethod
    def params_changed(cls, panel: Dict, graph):
        """Call after volts/amps changed on a live generator."""
        if panel.get('live') and panel.get('state') != 'tripped':
            panel['overload'] = False
            cls.dispatch(panel, 'gen:params', {'volts': panel.get('volts'), 'amps': panel.get('amps')})
            graph.emit(panel, {'v': panel.get('volts', 240), 'a': panel.get('amps', 13)})
            graph.update_all_gen_draws()

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev           = panel.get('state', 'off')
        panel['live']  = False
        panel['state'] = 'off'
        panel['overload'] = False
        cls.dispatch(panel, 'gen:reset', {'from': prev})
        graph.emit(panel, None)
        graph.update_all_gen_draws()

    @classmethod
    def on_draw_updated(cls, panel: Dict, graph):
        """Hook called by graph.compute_gen_draw() after BFS. Emits telemetry."""
        state = panel.get('state', 'off')
        last  = panel.get('_last_emitted_state')
        if state != last:
            if state == 'tripped':
                cls.dispatch(panel, 'gen:tripped', {
                    'drawAmps': round(panel.get('drawAmps', 0), 2),
                    'ratedAmps': panel.get('amps', 13),
                })
            elif state == 'sag':
                cls.dispatch(panel, 'gen:sag', {
                    'drawAmps': round(panel.get('drawAmps', 0), 2),
                    'ratedAmps': panel.get('amps', 13),
                })
            cls.dispatch(panel, 'state:change', {'from': last or 'off', 'to': state})
            panel['_last_emitted_state'] = state
        if panel.get('live'):
            cls.throttle(panel, 'gen:draw', {
                'drawWatts': panel.get('drawWatts', 0),
                'drawAmps':  round(panel.get('drawAmps', 0), 2),
                'ratedAmps': panel.get('amps', 13),
            })


NodeRegistry.register(Generator)
