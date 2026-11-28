"""
README - Python Power Graph Implementation
============================================================

A faithful Python port of the JavaScript power-2 simulation engine.

## Overview

The Python Power Graph is an event-driven simulation system for modeling
electrical power distribution networks. It accurately propagates electrical
signals (voltage/amperage) through a graph of nodes representing electrical
components (generators, loads, bulbs, breakers, etc.).

### Key Features

✓ **Signal Propagation** - Real-time voltage and current flow through the network
✓ **Wire Resistance** - Accurate resistive voltage drop based on wire type and length
✓ **Generator Draw Calculation** - BFS-based load calculation for generator management
✓ **Event System** - Pub/sub event monitoring for all simulation activities
✓ **Async Execution** - Non-blocking async tick loop for simulation updates
✓ **Node Registry** - Extensible system for adding new node types
✓ **State Serialization** - Save/load simulation state to JSON

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   PowerGraph Engine                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Panel Management | Signal Propagation | Async Loop│  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
        │                      │                    │
        ▼                      ▼                    ▼
   ┌─────────┐  ┌──────────────────────┐  ┌──────────────┐
   │ Panels  │  │ Node Registry        │  │ Edge Store   │
   │ (State) │  │ (Type → Class Map)   │  │ (Wires)      │
   └─────────┘  └──────────────────────┘  └──────────────┘
        │                      │                    │
        └──────────────────────┼────────────────────┘
                               ▼
                        ┌──────────────┐
                        │ Event System │
                        │ (Monitoring) │
                        └──────────────┘

Node Flow:
  Source Node → emit(signal)
              → EdgeStore.apply_edge(resistance)
              → Target Node.receive(transformed)
              → combine_sources(all inputs)
              → NodeClass.apply(combined_signal)
              → emit(outbound signal) → [repeat]
```

## File Structure

```
power_graph/
  __init__.py              # Package root, exports main classes
  event_system.py          # EventEmitter, EventMonitor, Event
  edge_store.py            # EdgeStore (wire properties & resistance)
  node_base.py             # NodeBase (base class for all nodes)
  node_registry.py         # NodeRegistry (type → class mapping)
  graph.py                 # PowerGraph (main engine)
  nodes/
    __init__.py
    generator.py           # Gen node (power source)
    bulb.py                # Bulb node (simple load)
    load.py                # Load node (scalable consumer)
    breaker.py             # Breaker node (overcurrent protection)
```

## Quick Start

```python
import asyncio
from power_graph import PowerGraph, NodeRegistry
from power_graph.nodes import Generator, Bulb, Load

# Create a graph
graph = PowerGraph()

# Spawn nodes
gen = graph.spawn('gen', label='Generator')
gen['volts'] = 240
gen['amps'] = 13
gen['live'] = True

bulb = graph.spawn('bulb', label='Light')
bulb['watts'] = 60

# Connect them with a wire
graph.connect(gen, 0, bulb, 0, wireType='copper', length=100)

# Run simulation for 5 seconds at 60 FPS
async def main():
    await graph.run(duration=5, fps=60)

asyncio.run(main())
```

## Core Components

### PowerGraph

Central simulation engine. Manages:
- Panel spawning/removal
- Signal propagation and combining
- Connection topology
- Generator draw calculations
- Async tick loop
- State serialization (save/load)

**Key Methods:**
- `spawn(type, label, preset)` - Create a node
- `connect(from_panel, from_pip, to_panel, to_pip, **props)` - Wire nodes
- `emit(panel, signal)` - Forward signal downstream
- `receive(panel, signal, source_id, in_pip)` - Process incoming signal
- `combine_sources(sources)` - Fold multiple inputs into one
- `run(duration, fps)` - Async simulation loop

### NodeBase

Root class for all node implementations. Provides:
- Static factory method `defaults(id, preset)`
- Signal processing via `apply(panel, signal, graph)`
- Per-frame updates via `tick(panel, dt, graph)`
- Inrush current (spike) handling
- Voltage ripple effects
- Serialization field specification

**Creating New Node Types:**
```python
from power_graph import NodeBase, NodeRegistry

class MyNode(NodeBase):
    type = 'mytype'
    label = 'My Node'
    group = 'Custom'
    catalog = [{'key': 'std', 'label': 'Standard'}]

    @classmethod
    def defaults(cls, node_id, preset=None):
        base = super().defaults(node_id, preset)
        base.update({
            'myProperty': preset.get('myProperty', 'default')
        })
        return base

    @classmethod
    def apply(cls, panel, signal, graph):
        # Your logic here
        graph.emit(panel, signal)

    @classmethod
    def tick(cls, panel, dt, graph):
        # Per-frame update
        pass

NodeRegistry.register(MyNode)
```

### EdgeStore

Manages wire (connection) properties and calculates resistance:

**Wire Types:**
- `copper`: 0.005 Ω/unit (most conductive)
- `aluminium`: 0.010 Ω/unit
- `steel`: 0.080 Ω/unit
- `lossy`: 0.300 Ω/unit (least conductive)

**Resistance Calculation:**
```
R (Ω) = (length_px / 100) × ohms_per_unit

V_drop = I × R
V_out = V_in - V_drop

If V_out ≤ 0, signal is absorbed (returns None)
```

**Methods:**
- `apply_edge(signal, conn_key)` - Transform signal through wire
- `compute_resistance(edge)` - Calculate Ω
- `get_wire_types()` - Get catalog
- `update(key, props)` - Set wire properties

### NodeRegistry

Singleton mapping from node type strings to node classes:

**Methods:**
- `register(NodeClass)` - Register a node type
- `get(type)` - Get class by type
- `create(type, id, preset)` - Factory method
- `catalog()` - All available presets
- `all_types()` - List of registered types

### EventSystem

Pub/sub event emission for monitoring:

**Methods:**
- `emitter.on(event_type, callback)` - Subscribe
- `emitter.emit(type, label, data)` - Publish
- `emitter.get_log()` - Event history
- `monitor.get_events(type, limit)` - Query events
- `monitor.get_stats()` - Event statistics

**Common Events:**
- `graph:spawn` - Node created
- `graph:remove` - Node removed
- `graph:connect` - Connection made
- `graph:disconnect` - Connection broken
- `graph:emit` - Signal forwarded
- `node:tick` - Node frame update
- `node:apply` - Signal applied
- `graph:start` - Simulation started
- `graph:stop` - Simulation stopped

## Signal Format

Signals are represented as dictionaries:
```python
signal = {
    'v': 240,    # Voltage in volts
    'a': 13      # Current in amps
}
```

Or `None` when there's no power (disconnected/off/tripped).

## Practical Examples

### Example 1: Simple Circuit

```python
graph = PowerGraph()

# Power source
gen = graph.spawn('gen', label='Generator')
gen['volts'] = 240
gen['amps'] = 15
gen['live'] = True

# Loads
bulb1 = graph.spawn('bulb', label='Light 1', preset={'watts': 60})
bulb2 = graph.spawn('bulb', label='Light 2', preset={'watts': 100})

# Wire them in parallel
graph.connect(gen, 0, bulb1, 0)
graph.connect(gen, 0, bulb2, 0)

# Run for 10 seconds
await graph.run(duration=10)
```

### Example 2: Protection Circuit

```python
graph = PowerGraph()

gen = graph.spawn('gen', label='Generator')
gen['volts'] = 240
gen['amps'] = 20
gen['live'] = True

breaker = graph.spawn('breaker', label='Main Breaker')
breaker['ratingAmps'] = 15

load = graph.spawn('load', label='High Power Load')
load['watts'] = 4000  # Would draw 16.7A - exceeds breaker rating

# Breaker protects the load
graph.connect(gen, 0, breaker, 0)
graph.connect(breaker, 0, load, 0)

await graph.run(duration=5)
# Breaker will trip when load current exceeds 15A
```

### Example 3: Long Distance Wire Drop

```python
graph = PowerGraph()

gen = graph.spawn('gen', label='Generator')
gen['volts'] = 240
gen['amps'] = 10
gen['live'] = True

bulb = graph.spawn('bulb', label='Remote Light')
bulb['watts'] = 60

# Very long wire (lossy)
graph.connect(gen, 0, bulb, 0, wireType='lossy', length=5000)

await graph.run(duration=5)
# Bulb may not light due to excessive voltage drop
```

### Example 4: Event Monitoring

```python
graph = PowerGraph()
monitor = EventMonitor(graph.emitter)

# Listen to specific events
def on_node_apply(event):
    print(f"Signal applied to {event.label}: {event.data}")

graph.emitter.on('node:apply', on_node_apply)

# ... create nodes and run ...

# Get statistics
stats = monitor.get_stats()
print(f"Total events: {stats['total_events']}")
print(f"Event types: {stats['event_counts']}")
```

## Testing

Run the test suite:
```bash
python test_basics.py
```

Tests validate:
- ✓ Node creation
- ✓ Connections and wiring
- ✓ Signal propagation
- ✓ Resistance calculations
- ✓ Source combining
- ✓ Generator draw BFS
- ✓ Connection removal

## Physics Model

### Signal Propagation

The graph models electrical power flow with a dominant-rail voltage model:

**Combining Sources:**
- Voltage: `max(all_sources)` — highest voltage wins (dominant rail)
- Amperage: `sum(all_sources)` — amps add in parallel

**Resistance:**
- V_out = V_in - (I × R)
- If V_out ≤ 0, no power (wire too resistive)

**Generator Loading:**
- BFS traversal from each generator
- Sum load wattage with 1/N sharing for shared loads
- Generators sag at 1.0x+ amps, trip at 1.3x+ amps

### Node Behaviors

**Generator**
- Emits fixed V/A when live=true
- Sags when >100% loaded
- Trips when >130% loaded

**Bulb**
- Turns on above minVolts threshold
- Draws watts = power consumed
- Has warm-up inrush spike (50% for 0.2s)

**Load**
- Dynamic scalable consumer
- Larger inrush spike (200% for 0.5s)
- BFS counts its wattage for generator draw

**Breaker**
- Passes signal through normally
- Trips (blocks) if current exceeds rating
- Must be manually reset

## Performance

### Designed for Real-time Interactive Simulation

- **Target FPS:** 60 frames per second (configurable)
- **Frame Time:** ~16.6 ms per frame
- **Time Step:** Capped at 100 ms (handles pause/resume)
- **Cycle Guard:** Prevents infinite loops in ring topologies
- **Event Filtering:** Optional event monitoring overhead

### Scalability Considerations

- Linear complexity in number of nodes (for tick loop)
- Linear complexity in number of connections (per signal emit)
- BFS complexity: O(nodes + edges) per generator (once per frame)
- Event filtering is optional (off by default)

## Next Steps

The core framework is complete. Future iterations could add:

1. **Converter Nodes** - AC/DC conversion, frequency, phase
2. **Battery Nodes** - Rechargeable storage with charge curves
3. **Decision Nodes** - Logic-based routing (conditional flows)
4. **Meter Nodes** - Measurement and monitoring
5. **Three-Phase Support** - 3Φ power modeling
6. **Harmonics** - Voltage/current distortion
7. **Protection Logic** - Fault detection and coordination
8. **GUI Integration** - Visual simulation interface
9. **Optimization** - Caching, spatial partitioning
10. **Advanced Serialization** - Binary format, version management

## License

Same as parent project.

## See Also

- `test_basics.py` - Core functionality tests
- `example_basic.py` - Full async simulation example
- `power_graph/nodes/` - Node implementation examples
- `func-pipes/static/js/power2/` - Original JavaScript implementation

"""

if __name__ == '__main__':
    print(__doc__)
