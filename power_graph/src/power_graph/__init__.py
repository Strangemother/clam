"""
Python Power Graph System
──────────────────────────────────────────────────────────────────────────────
A faithful port of the JavaScript power-2 simulation engine to Python.

Core components:
  - PowerGraph: Central signal propagation engine
  - NodeBase: Base class for all node types
  - NodeRegistry: Type → class mapping singleton
  - EdgeStore: Wire properties and resistance calculations
  - Event system: Pub/sub for monitoring and debugging

Usage:
    from power_graph import PowerGraph, NodeRegistry
    from power_graph.nodes import Generator, Bulb

    # Register node types
    NodeRegistry.register(Generator)
    NodeRegistry.register(Bulb)

    # Create graph
    graph = PowerGraph()

    # Add nodes and connections
    gen = graph.spawn('gen', label='Power Source')
    bulb = graph.spawn('bulb', label='Light')
    graph.connect(gen, 0, bulb, 0, wireType='copper')

    # Run simulation
    import asyncio
    asyncio.run(graph.run(duration=10))
"""

from .event_system import EventEmitter, EventMonitor
from .edge_store import EdgeStore, WIRE_TYPES
from .node_registry import NodeRegistry
from .node_base import NodeBase, Signal
from .graph import PowerGraph

# Import all node types so they self-register via NodeRegistry.register()
from . import nodes  # noqa: F401

__all__ = [
    'PowerGraph',
    'NodeBase',
    'NodeRegistry',
    'EdgeStore',
    'WIRE_TYPES',
    'Signal',
    'EventEmitter',
    'EventMonitor',
]

__version__ = '0.1.0'
