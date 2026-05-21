# logic/

Boolean logic graph. Route binary signals (`'0'` / `'1'`) through gates,
switches, and LED indicators.

Route: `/logic`

## Signal format

String `'0'` or `'1'`. No wrapper object.

## Node types

| Type | Pips | Description |
|------|------|-------------|
| `gate` | A in, B in → out | Logical gate. Op selected from dropdown |
| `switch` | → out | Manual toggle source. Click to flip `'0'`/`'1'` |
| `led` | in → | Sink indicator. Shows ON/OFF based on received value |

## Gate node fields

| Field | Type | Notes |
|-------|------|-------|
| `op` | string | Gate operation name. Must exist on `LogicNodes` |
| `inputs` | array | `[valueOnPip0, valueOnPip1]` — updated as signals arrive |
| `state` | string | Last output of the gate (`'0'`, `'1'`, or `'?'` initial) |

## Gate operations (`LogicNodes` class)

Method signature: `(input, stored) → '0' | '1'`

- `input` — value that just arrived on the active pip
- `stored` — the other input (latched from last update)

Current gates: `buffer`, `not`, `and`, `or`, `nand`, `nor`, `xor`, `xnor`

`UNARY_GATES = new Set(['buffer', 'not'])` — these only use `input` and
ignore `stored`. Used to hide the second pip in the UI.

All gate names come from `logicGateOps`, built via `Object.getOwnPropertyNames`
at startup. Add a method to `LogicNodes` and it appears automatically.

## Switch panel fields

| Field | Type | Notes |
|-------|------|-------|
| `state` | string | `'0'` or `'1'`. Toggle with `toggleSwitch(panel)` |

Switch has no inbound pips. `_emitFromNode(panel)` fires its current state
downstream whenever toggled.

## LED panel fields

| Field | Type | Notes |
|-------|------|-------|
| `state` | string | `'0'` or `'1'`. Updated on every received signal |

LED has no outbound pips — it is a pure sink.

## Method groups

| File | Exported as | Responsibility |
|------|-------------|----------------|
| `nodes.js` | `LogicNodes`, factories | Gate ops, `UNARY_GATES`, `logicGateOps`, panel factories |
| `index.js` | Vue app | Wiring, `receive`, `_applyGate`, `toggleSwitch`, `_emitFromNode` |

## `data()` keys

- `logicGateOps` — populated from `logicGateOps` array, drives the op dropdown
- No separate signal file — all routing is inline in `index.js`

## Gate evaluation detail

When a signal arrives on pip index `i`:
1. `panel.inputs[i]` is updated to the new value.
2. If unary gate: `op(input, stored)` runs with stored = `'0'`.
3. If binary gate: `op(panel.inputs[0], panel.inputs[1])` runs.
4. Result stored in `panel.state` and emitted downstream.

## Adding a new gate

1. Add a method to `LogicNodes` in `nodes.js`.
   - Unary: add its name to `UNARY_GATES` too.
2. Done — the dropdown and routing update automatically.
