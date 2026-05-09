# plugs/

Watt-based power distribution. Model batteries, modules, and meters using a
simplified two-pip per node topology.

Route: `/plugs`

## Signal format

Plain number (watts). No wrapper object.

## Node topology

Every node has exactly **2 inbound pips** and **2 outbound pips**:

| Pip index | Role |
|-----------|------|
| 0 | Power channel |
| 1 | Auxiliary / secondary passthrough |

`receive(panel, value, pipIndex)` — `value` is a plain number, not an object.
`pipIndex` selects which channel the value updates.

## Node types

| Type | Description |
|------|-------------|
| `battery` | Source. Emits `watts` on outbound pip 0 when fired. `outputEdges` tracks per-edge split distribution |
| `module` | Consumer. Accumulates incoming watts in `powerSources`, subtracts `usage`, forwards remainder on outbound pip 0 |
| `meter` | Instrument. Accumulates `powerSources`, shows current and peak. Bar display scales against `METER_SCALE` |

## Battery panel fields

| Field | Default | Notes |
|-------|---------|-------|
| `watts` | 100 | Configurable output power |
| `state` | 0 | Last emitted value |
| `connectionCount` | 0 | Outbound connections at last fire |
| `outputEdges` | `[]` | `[{ targetId, watts }]` — per-edge split table |

## Module panel fields

| Field | Default | Notes |
|-------|---------|-------|
| `usage` | 20 | Watts consumed |
| `powerIn` | 0 | Sum of all sources received |
| `powerUsed` | 0 | `Math.min(usage, powerIn)` |
| `powerOut` | 0 | `powerIn - powerUsed` — forwarded downstream |
| `powerSources` | `{}` | `{ [sourceId]: watts }` — accumulated per sender |

## Meter panel fields

| Field | Default | Notes |
|-------|---------|-------|
| `state` | 0 | Sum of all inbound sources |
| `peak` | 0 | Highest sum seen since last reset |
| `powerSources` | `{}` | `{ [sourceId]: watts }` per sender |

## `METER_SCALE`

```js
const METER_SCALE = 500  // watts at 100% bar fill
```

Change in `index.js` to suit your expected power range.

## Method groups

| File | Exported as | Responsibility |
|------|-------------|----------------|
| `nodes.js` | panel factories | `makeBatteryPanel`, `makeModulePanel`, `makeMeterPanel` |
| `index.js` | Vue app | `receive`, `_applyBattery`, `_applyModule`, `_applyMeter`, `fire`, wiring, persist |

## `powerSources` accumulation

Multiple upstream nodes can connect to the same module or meter.
Rather than summing signals blindly (which would double-count on re-propagation),
each sender's latest value is stored separately in `powerSources[sourceId]`.
The total is `Object.values(panel.powerSources).reduce((s,v)=>s+v, 0)`.

Reset `powerSources[sourceId] = 0` when a wire is disconnected.

## How plugs differs from power/

`plugs` is simpler and more abstracted — no voltage/amps split, no BFS overload
detection, no wire resistance. Use it when you only care about watts throughput
and don't need detailed electrical modelling.

## Adding a new node type

1. Add factory in `nodes.js`.
2. Add `addFoo` + `resetPanel` branch in `index.js` (spawn section).
3. Add `_applyFoo` and call it from `receive`.
4. Add template block in `plugs.html`.
