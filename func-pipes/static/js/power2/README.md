# power2/

Class-based, registry-driven power backbone simulation.  
Route: `/power2`

## Architecture

```
core/
  node-base.js       NodeBase class — root of all node types
  node-registry.js   NodeRegistry — maps type → class; aggregates catalog
  edge-store.js      EdgeStore2  — per-wire properties (resistance, enable)
  graph.js           Graph       — signal propagation, tick, wiring, persist

nodes/
  gen.js             Generator  (extends NodeBase)
  breaker.js         Breaker    (extends NodeBase)
  bulb.js            Bulb       (extends NodeBase)
  load.js            Load       (extends NodeBase)  ← base for consumers
  meter.js           Meter      (extends NodeBase)
  converter.js       Converter  (extends NodeBase)
  heater.js          Heater     (extends Load)  ← custom example
  console-node.js    ConsoleNode (extends Load) ← custom example

index.js             Vue app bootstrap
```

## Class hierarchy

```
NodeBase
├── Generator     — source; produces { v, a }; no inbound pip
├── Breaker       — manual switch with auto-trip
├── Bulb          — resistive lamp sink; no outbound pip
├── Meter         — transparent read-only instrument
├── Converter     — step-up / step-down with efficiency model
└── Load          — generic consumer with capacitor buffer
    ├── Heater    — Load + thermal simulation (temperature, heatState)
    └── ConsoleNode — Load + boot sequence (booting → ready → shutdown)
```

## Adding a new node type (5 steps)

1. **Create** `js/power2/nodes/mynode.js` extending `NodeBase` or `Load`:

```js
class MyNode extends Load {
    static type  = 'mynode'
    static label = 'My Node'
    static group = 'MyGroup'

    static catalog = [
        { key: 'mynode-sm', label: 'My Node (SM)', watts: 50, minVolts: 180 },
    ]

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            myField: preset.myField ?? 'default',
        }
    }

    static configFields() {
        return [...super.configFields(), 'myField']
    }

    // Custom per-frame behaviour
    static tick(panel, dt, graph) {
        super.tick(panel, dt, graph)  // keep capacitor logic
        // your additions here
    }

    // Custom reset
    static reset(panel, graph) {
        panel.myField = 'default'
        super.reset(panel, graph)
    }
}
NodeRegistry.register(MyNode)
```

2. **Add** a `<script>` tag in `power2.html` before `index.js`:
```html
<script src="{{ url_for('static', filename='js/power2/nodes/mynode.js') }}"></script>
```

3. **Add** a toolbar button in the `<div id="toolbar">` section:
```html
<button @click="addType('mynode')">🔧 MyNode</button>
```

4. **Add** a template block inside `<div id="panels">`:
```html
<template v-else-if="panel.type === 'mynode'">
    <div class="node-body">
        <!-- your UI here -->
    </div>
</template>
```

5. **That's it.** The catalog dropdown, save/load, reproduce, edge inspector, ripple —
   all work automatically through the registry.

## Node interface (static methods on NodeBase)

| Method | Required | Description |
|--------|----------|-------------|
| `type` | ✓ | Unique string key |
| `label` | ✓ | Display name |
| `group` | — | Toolbar group |
| `catalog` | — | Preset entries array |
| `defaults(id, preset)` | ✓ | Returns initial panel state object |
| `configFields()` | — | Fields to save/restore |
| `apply(panel, signal, graph)` | — | Signal processor; must call `graph.emit()` |
| `tick(panel, dt, graph)` | — | Per-frame update |
| `reset(panel, graph)` | — | Restore clean state |

## Extensibility flags

| Static field | On class | Effect |
|---|---|---|
| `static consumesWatts = true` | `Load` (inherited) | Generator BFS counts this node's `watts` draw |

## Signal format

```js
{ v: number, a: number }   // volts, amps available
null                        // no power / open circuit
```

## Key differences from power v1

| v1 | v2 |
|----|-----|
| Plain object factories | Class `defaults()` factory |
| Mixin method groups (`SpawnMethods`, etc.) | Single `Graph` class |
| Type-switch dispatch (`if type==='bulb'`) | Registry dispatch (`NodeRegistry.get(type).apply()`) |
| Hard-coded catalog in `nodes.js` | Each node embeds its own catalog |
| Hard-coded type list in BFS | `static consumesWatts` flag |
| New type = edit 6 files | New type = 1 file + HTML additions |
