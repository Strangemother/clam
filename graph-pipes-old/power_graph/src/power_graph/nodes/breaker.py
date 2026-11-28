"""
nodes/breaker.py
──────────────────────────────────────────────────────────────────────────────
Circuit Breaker — makes/breaks circuit based on rated current.

States: 'off' | 'closed' | 'open' | 'tripped'

  closed  — normal on state; passes signal through
  open    — manually opened; blocks signal
  tripped — overcurrent protection activated; blocks signal
  off     — no power ever received

Behaviour
  toggle()   closes (or opens) the breaker; if tripped, first call → 'open'
  reset()    forces back to 'closed' state

For single-unit variants, subclass and set a new type:

    class Relay(Breaker):
        type   = 'relay'
        label  = 'Relay'
        catalog = [{'key': 'relay', 'label': 'Relay 10A', 'ratingAmps': 10}]
    NodeRegistry.register(Relay)
"""

from typing import Dict, List
from power_graph.node_base import NodeBase, Signal
from power_graph.node_registry import NodeRegistry


class Breaker(NodeBase):
    """Circuit breaker that trips on overcurrent."""

    type  = 'breaker'
    label = 'Breaker'
    group = 'Protection'
    dispatch_delay = 150

    catalog = [
        {'key': 'breaker-6a',  'label': 'Breaker 6A',  'ratingAmps': 6 },
        {'key': 'breaker-13a', 'label': 'Breaker 13A', 'ratingAmps': 13},
        {'key': 'breaker-30a', 'label': 'Breaker 30A', 'ratingAmps': 30},
    ]

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        if preset is None:
            preset = {}
        base = super().defaults(node_id, preset)
        base.update({
            'ratingAmps': preset.get('ratingAmps', 13),
            'closed':     True,
            'tripped':    False,
            'state':      'closed',
        })
        return base

    @classmethod
    def config_fields(cls) -> List[str]:
        return [*super().config_fields(), 'ratingAmps', 'closed']

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        if not panel.get('closed', True) or panel.get('tripped', False):
            # Open or tripped — block signal
            state_key = 'tripped' if panel.get('tripped') else 'open'
            if panel['state'] != state_key:
                panel['state'] = state_key
                cls.dispatch(panel, 'state:change', {'state': state_key})
            graph.emit(panel, None)
            return

        if signal is None:
            if panel['state'] != 'off':
                panel['state'] = 'off'
            graph.emit(panel, None)
            return

        amps   = signal.get('a', 0)
        rating = panel.get('ratingAmps', 13)

        if amps > rating:
            panel['tripped'] = True
            panel['closed']  = False
            prev             = panel['state']
            panel['state']   = 'tripped'
            cls.dispatch(panel, 'breaker:tripped', {'amps': amps, 'rating': rating})
            cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'tripped'})
            graph.emit(panel, None)
        else:
            if panel['state'] != 'closed':
                cls.dispatch(panel, 'state:change', {'from': panel['state'], 'to': 'closed'})
                panel['state'] = 'closed'
            graph.emit(panel, signal)

    @classmethod
    def toggle(cls, panel: Dict, graph):
        """Open/close the breaker. If tripped, first toggle clears trip → open."""
        if panel.get('tripped'):
            panel['tripped'] = False
            panel['closed']  = False
            prev             = panel['state']
            panel['state']   = 'open'
            cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'open'})
            graph.emit(panel, None)
            return

        panel['closed'] = not panel.get('closed', True)
        prev            = panel['state']
        panel['state']  = 'closed' if panel['closed'] else 'open'
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': panel['state']})

        if panel['closed']:
            # Re-propagate from upstream sources
            sources  = panel.get('powerSources', {})
            combined = graph.combine_sources(sources) if sources else None
            cls.apply(panel, combined, graph)
        else:
            graph.emit(panel, None)

    @classmethod
    def reset(cls, panel: Dict, graph):
        prev             = panel['state']
        panel['tripped'] = False
        panel['closed']  = True
        panel['state']   = 'closed'
        panel['powerSources'] = {}
        cls.dispatch(panel, 'state:change', {'from': prev, 'to': 'closed'})
        graph.emit(panel, None)


class Relay(Breaker):
    """
    Relay — normally-open, electrically controlled switch.

    Inherits Breaker logic fully; single-unit class demonstrates the
    single-unit pattern (subclass family, new type/catalog).
    """
    type    = 'relay'
    label   = 'Relay'
    catalog = [
        {'key': 'relay',     'label': 'Relay 10A',  'ratingAmps': 10},
        {'key': 'relay-30a', 'label': 'Relay 30A',  'ratingAmps': 30},
    ]


NodeRegistry.register(Breaker)
NodeRegistry.register(Relay)
