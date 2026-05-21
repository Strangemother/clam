# power/

Electrical power backbone simulation. Route voltage and current through a
network of generators, breakers, loads, and instruments.

Route: `/power`

## Signal format

```js
{ v: number, a: number }  // volts, amps available
null                       // no power / upstream open
```

## Node types

| Type | Pips | Description |
|------|------|-------------|
| `gen` | → out | Power source. Configurable volts and amps. Toggle on/off |
| `breaker` | in → out | Manual open/close. Trips automatically if amps exceed rating |
| `bulb` | in → | Resistive lamp (sink). Brightness proportional to received watts |
| `load` | in → out | Generic consumer. Has `watts`, `minVolts`, optional `capacitance` |
| `meter` | in → out | Read-only instrument. Displays V/A/W; passes signal through unchanged |

## Panel fields (common)

| Field | Type | Notes |
|-------|------|-------|
| `state` | string | `'idle'` \| `'active'` \| `'tripped'` |
| `pipsInbound` | array | `[{ label: panelId, index: 0 }]` |
| `pipsOutbound` | array | same shape |

## Generator-specific

| Field | Default | Notes |
|-------|---------|-------|
| `volts` | 240 | Output voltage |
| `amps` | 13 | Max current |
| `running` | false | Toggle with `toggleGen(panel)` |

## Breaker-specific

| Field | Default | Notes |
|-------|---------|-------|
| `closed` | true | Open/close with `toggleBreaker(panel)` |
| `ratingAmps` | 13 | Trips if incoming amps exceed this |
| `tripped` | false | Reset by opening then closing |

## Load-specific

| Field | Default | Notes |
|-------|---------|-------|
| `watts` | 100 | Power consumed |
| `minVolts` | 200 | Below this the load shows inactive |
| `capacitance` | 0 | Charge buffer in watt-seconds. Drains via rAF tick |
| `charge` | 0 | Current charge level |

## Method groups

| File | Exported as | Responsibility |
|------|-------------|----------------|
| `power-spawn.js` | `SpawnMethods` | Add, remove, reset panels |
| `power-signal.js` | `SignalMethods` | Propagate `{ v, a }` signals, combine multiple sources (sum) |
| `power-gen.js` | `GenMethods` | Generator BFS overload resolution |
| `power-nodes.js` | `NodeMethods` | Per-type apply logic (bulb brightness, load state, etc.) |
| `power-tick.js` | `TickMethods` | rAF loop for capacitor drain |
| `power-wiring.js` | `WiringMethods` | Pip drag-drop, connect, EdgeStore writes |
| `power-persist.js` | `PersistMethods` | Save/load/export/import via localStorage or JSON file |
| `nodes.js` | — | Factories and `COMPONENT_CATALOG` |
| `power-edges.js` | `EdgeStore` | IIFE. Stores per-wire resistance and type. `EdgeStore.get(key)` |
| `power-save.js` | `PowerSave` | Low-level JSON serialiser. Used by `PersistMethods` |

## Adding a new node type

1. Add a factory `makeFooPanel(id, p)` in `nodes.js`.
2. Add a catalogue entry with `type: 'foo'` and a group label.
3. Add `addFoo()` + catalog branch in `power-spawn.js`.
4. Add `_applyFoo(panel, signal)` in `power-nodes.js`, call it from
   `_applyNode` dispatch.
5. Add a reset branch in `resetPanel`.
6. Add a serialisation branch in `power-persist.js`.
7. Add a template block in `power.html`.

## Things to watch

- Signal combines **sum** amps from multiple upstream sources into one `{ v, a }`.
  This is different from `inputs/` and `prompting/` which use first-wins.
- The EdgeStore tracks wire types (`copper`, `thin`, etc.) which affect
  resistance. Stored in the save file as `edges`.
- `NOMINAL_VOLTS = 240` is used for W→A conversion throughout. Change it in
  `nodes.js` if you model a different grid.
