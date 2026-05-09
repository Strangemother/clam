# inputs/

Gamepad and sensor input routing with numeric signal processing. Connect
browser Gamepad API events to downstream compute or display nodes.

Route: `/inputs`

## Signal format

```js
{ value: number | boolean }   // numeric 0–1, analogue axes, or button boolean
null                           // no signal / disconnected
```

## Node types

| Type | Pips | Description |
|------|------|-------------|
| `gamepad` | → 20 out | Reads from Gamepad API. One outbound pip per button/axis (A, B, X, Y, LB, RB, LT, RT, Select, Start, L3, R3, D↑↓←→, LX, LY, RX, RY) |
| `value` | in → | Numeric sink. Displays received value with a simple bar indicator |
| `compute` | N in → M out | Named in/out pips, user-defined `fn`, optional gate |

## Outbound pip index mapping (gamepad)

Index 0–15 are buttons in standard Gamepad API order.
Index 16–19 are axes: LX, LY, RX, RY.
`GAMEPAD_PIP_DEFS` in `nodes.js` is the canonical list.

## Compute node fields

| Field | Type | Notes |
|-------|------|-------|
| `fnSrc` | string | Function body — edited in the panel textarea |
| `values` | object | `{ [pipName]: number }` — current value of each inbound pip |
| `gatePip` | string \| null | Pip name that controls gating. `null` = always run |
| `gateMode` | string | `'above'` \| `'below'` \| `'nonzero'` \| `'always'` |
| `gateThresh` | number | Threshold value for above/below modes |
| `fnError` | string \| null | Last error from `new Function()` eval, or null |

## Compute function signature

```js
fn(value, name, inputs) => scalar | { pipName: value } | null
```

- `value` — new value on the pip that just changed
- `name` — string name of that pip (e.g. `'X'`)
- `inputs` — snapshot of all current pip values `{ name: value }`
- Return a scalar to emit the same value on **all** outbound pips
- Return a named object to route to **specific** pips by name
- Return `null` to suppress downstream propagation

## COMPUTE_PRESETS

15 built-in presets in `inputs-compute.js`: Identity, Absolute, Negate, Sign,
Clamp 0–1, Clamp −1–1, Square, √ signed, Smoothstep, Ease in-out cos,
Scale ×10, Bool (≥0.5), XY→Magnitude, XY→Angle, XY→Normalise.

Select via the dropdown or pass a `fnSrc` in the catalogue entry directly.

## Method groups

| File | Exported as | Responsibility |
|------|-------------|----------------|
| `inputs-spawn.js` | `SpawnMethods` | Add, remove, reset panels |
| `inputs-signal.js` | `SignalMethods` | Route `{value}` signals; thread `inPipIndex` through `_emitFromPip` |
| `inputs-compute.js` | `ComputeMethods` | Gate check, `new Function()` eval, `COMPUTE_PRESETS` |
| `inputs-gamepad.js` | `GamepadMethods` | `requestAnimationFrame` poll loop, `connectGamepad` |
| `inputs-wiring.js` | `WiringMethods` | Pip drag-drop, connect; wire color `#66aaff` |
| `inputs-persist.js` | `PersistMethods` | Save/load/export via localStorage |
| `nodes.js` | — | Factories, `GAMEPAD_PIP_DEFS`, `COMPONENT_CATALOG` |

## Named pip routing detail

`inPipIndex` is threaded from `_emitFromPip` all the way into `receive`.
The receiving compute node maps `inPipIndex → pipName` via its `pipsInbound`
array, then updates `panel.values[pipName]` before running the function.
This is how multi-input compute works (e.g. XY→Magnitude).

## Adding a new compute preset

Add an object to `COMPUTE_PRESETS`:

```js
{ label: 'My Preset', src: 'return value * 2' }
```

It will appear automatically in the UI dropdown. No other changes needed.

## Adding a new node type

Same pattern as `power/`:
1. Factory in `nodes.js` + catalogue entry
2. `addFoo` + `resetPanel` branch in `inputs-spawn.js`
3. `_applyFoo` in `inputs-signal.js`, wired into `_applyNode`
4. Template block in `inputs.html`

## Things to watch

- Gamepad API only fires during an animation frame — the `requestAnimationFrame`
  poll in `inputs-gamepad.js` is single-entry (guarded by `_polling` flag).
  Call `connectGamepad()` from the UI button; disconnection cleans up automatically.
- The compute fn runs with `new Function()`. Intentional — local dev tool only.
  Never expose this to untrusted input.
- `panel.fnError` shows the last thrown error string. Check there first when the
  compute node stops emitting.
