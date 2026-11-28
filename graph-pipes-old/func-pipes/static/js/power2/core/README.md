# Power2 Core Architecture

This directory contains the four foundational modules that every node and the graph engine depend on. All node files in `nodes/` sit on top of these.

---

## Module Map

```
core/
├── node-base.js      — Root class for all node behaviour
├── node-registry.js  — Type-key → class lookup table
├── edge-store.js     — Per-wire resistance and enable/disable model
└── graph.js          — Central simulation engine
```

---

## Why State and Behaviour Are Separated

Node **state** lives in plain reactive Vue objects (`app.panels[]`).  
Node **behaviour** lives in static methods on each node class.

This split is deliberate:

- **Vue reactivity requires plain objects.** Vue 3's proxy-based reactivity cannot observe class instances directly. Keeping panel state as a plain `{}` means bindings, watchers, and computed properties work without any adapter code.
- **Static classes are stateless singletons.** Node classes hold no instance data. They are loaded once, never instantiated, and are trivially testable — pass a mock panel object and a mock graph.
- **Hot-loading works naturally.** A new node type is registered by dropping a `<script>` tag into the HTML. No bundler, no import map, no changes to the engine.

---

## `node-base.js` — NodeBase

The root class every node type extends (directly or indirectly).

**Responsibilities**

| Area | What it provides |
|---|---|
| `defaults(id, preset)` | Factory for the initial panel state object |
| `configFields()` | List of fields to persist through save/load |
| `apply(panel, signal, graph)` | Override hook — signal processing (no-op in base) |
| `tick(panel, dt, graph)` | Override hook — per-frame update (no-op in base) |
| `reset(panel, graph)` | Clears runtime state back to 'off' |
| `dispatch(panel, type, data)` | Debounced event dispatch to the event monitor |
| `throttle(panel, type, data)` | Fire-first throttled event dispatch |
| Spike helpers | `startSpike`, `tickSpike`, `spikeMultiplier` |

**Key convention — `_` prefix fields**

Fields prefixed with `_` (e.g. `_spikeTimer`, `_rippleAccum`) are internal runtime state. They are intentionally excluded from `configFields()` and are never persisted. Do not rely on them across save/load cycles.

---

## `node-registry.js` — NodeRegistry

A module-scoped Map from type-string keys to node classes.

```
NodeRegistry.register(MyClass)        // called at bottom of each node file
NodeRegistry.get('heater')            // → Heater class
NodeRegistry.create('heater', id, {}) // → fresh panel state object
NodeRegistry.catalog()               // → flat array of all catalog entries
NodeRegistry.catalogByGroup()        // → { 'Source': [...], 'Load': [...] }
```

The graph engine never imports node classes directly — it always goes through `NodeRegistry.get(panel.type)`. This means a new node type is fully available to the engine the moment its file is loaded, with no engine changes required.

---

## `edge-store.js` — EdgeStore2

Stores per-connection wire properties and applies signal transformations.

**Wire model**

Each connection (identified by a `connKey` string) has:

```js
{
  enabled:          bool        // false = broken wire → null signal
  wireType:         string      // key from WIRE_TYPES catalog
  length:           number      // screen distance in pixels (auto-measured)
  manualResistance: number|null // overrides computed resistance when set
}
```

**Resistance calculation**

```
R (Ω) = (length / PX_PER_UNIT) × ohmsPerUnit
V_out = V_in − (A × R)
A_out = A_in  (amps pass through unchanged)
```

If `V_out ≤ 0` the edge returns `null` (wire too resistive for the current load).

**Wire type catalog**

| Key        | Ω/unit | Colour   |
|------------|--------|----------|
| `copper`   | 0.005  | #00e87c  |
| `aluminium`| 0.010  | #aadd00  |
| `steel`    | 0.080  | #ff9900  |
| `lossy`    | 0.300  | #ff3333  |

---

## `graph.js` — PowerGraph

The central simulation engine. Holds no per-node logic — all of that is in the node classes.

**Responsibilities**

| Area | Key methods |
|---|---|
| Signal propagation | `receive()`, `emit()`, `emitTo()`, `combineSources()`, `repropagateAll()` |
| Generator draw BFS | `updateAllGenDraws()`, `computeGenDraw()` |
| Per-frame tick | `startTick()`, `stopTick()`, `_tickRipple()` |
| Pip wiring | `connect()`, `disconnect()`, `pipDrop()` |
| Panel lifecycle | `spawnPanel()`, `addType()`, `addFromCatalog()`, `remove()`, `reset()` |
| Save / load | `saveLayout()`, `loadLayout()`, `exportJSON()`, `importJSON()` |

**Signal propagation flow**

```
upstream node
    │  emit(panel, signal)
    ▼
EdgeStore2.applyEdge(signal, connKey)   ← resistance drop / wire enabled check
    │
    ▼
receive(targetPanel, transformed, sourceId, inPipIndex)
    │  stores signal in panel.powerSources[sourceId]
    │  combineSources() → single combined { v, a }
    ▼
NodeClass.apply(panel, combined, graph)
    │  node decides what to forward on outbound pip(s)
    ▼
emit() / emitTo()  ────────────────────► back to top for each downstream panel
```

Cycles are prevented by `_propagating` — a `Set` of panel IDs currently mid-receive. A panel will not process a second inbound signal until the first `apply()` call has returned.

**`combineSources()` folding rules**

- `v = max(all live source voltages)` — dominant-rail model; highest voltage sets the bus
- `a = sum(all live source amps)` — parallel supply; amps accumulate

**BFS generator draw**

`computeGenDraw()` walks the graph from each generator, summing load contributions via BFS. When a load is fed by N generators, its draw is divided by N so each generator sees only its proportional share. The final `drawAmps / amps` ratio determines whether the generator runs normally, sags, or trips.
