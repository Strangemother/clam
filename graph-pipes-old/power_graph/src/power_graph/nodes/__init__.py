"""
nodes/__init__.py
──────────────────────────────────────────────────────────────────────────────
Node type implementations for the power graph.

Each node type is a subclass of NodeBase that implements:
  - defaults(): Initial state factory
  - apply(panel, signal, graph): Signal propagation logic
  - tick(panel, dt, graph): Per-frame updates

Type families can have single-unit subclasses:
  Relay(Breaker), PowerRail(BusBar) — each registered separately.
"""

from .generator import Generator
from .bulb import Bulb
from .load import Load
from .breaker import Breaker, Relay
from .meter import Meter
from .converter import Converter
from .decision import Decision
from .bus_bar import BusBar, PowerRail
from .series_battery import SeriesBattery
from .heater import Heater
from .console import ConsoleNode

__all__ = [
    'Generator',
    'Bulb',
    'Load',
    'Breaker', 'Relay',
    'Meter',
    'Converter',
    'Decision',
    'BusBar', 'PowerRail',
    'SeriesBattery',
    'Heater',
    'ConsoleNode',
]
