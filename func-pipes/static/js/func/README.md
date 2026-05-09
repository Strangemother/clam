# func/

General-purpose text transform graph. Connect string-producing nodes through
named operations using `ExecNodes` or accumulated state via `ValueNode`.

Route: `/func`

## Signal format

Plain strings. No wrapper object — the value on the wire is always a string
(or empty string for no signal).

## Node types

| Type | Pips | Description |
|------|------|-------------|
| `exec` | in → out | Applies one `ExecNodes` method to the incoming string |
| `value` | in → out | Accumulates a stored internal value via a `ValueNode` combine op |
| `display` | in → | Sink. Renders the most recent string value in the panel |

## ExecNodes (`exec-nodes.js`)

A plain class. Each method is `fn(input: string) → string` (or `Promise<string>`).
The method name appears automatically in the dropdown — no other registration needed.

Current methods:
`passthrough`, `uppercase`, `lowercase`, `trim`, `reverse`,
`wordCount`, `charCount`, `lineCount`, `jsonFormat`

**To add a transform**: add a method to the class. That's it.

## ValueNode (`value-node.js`)

Stateful accumulator. Each node instance has a `storedValue` that persists between
upstream signals.

Method signature: `fn(input, stored) → string`

Current operations:
`append`, `prepend`, `replace`, `add`, `multiply`, `joinLines`, `joinCsv`, `max`, `min`

`replace` makes it a simple pass-through holder. `add` / `multiply` do numeric accumulation.

## Panel fields

| Field | Type | Notes |
|-------|------|-------|
| `fn` | string | Selected method name. Must match a key on `ExecNodes` / `ValueNode` |
| `storedValue` | string | ValueNode internal state |
| `lastOutput` | string | Last emitted value, shown in the panel |

## Method groups

| File | Exported as | Responsibility |
|------|-------------|----------------|
| `exec-nodes.js` | `ExecNodes` class | All string→string transforms |
| `value-node.js` | `ValueNode` class | Stateful combine operations |
| `index.js` | Vue app | Wires everything together; `execNodeNames` + `valueNodeOps` in `data()` |

## `data()` keys

- `execNodeNames` — built from `Object.getOwnPropertyNames(ExecNodes.prototype)`, populates the exec dropdown
- `valueNodeOps` — built from `ValueNode.prototype`, populates the value-node dropdown

## Forwarding

Uses `pipesWalker.getOutgoingIds(panelId)` (from `pipes-runtime.js`) to find
downstream panels and call `receive(panel, value, pipIndex)` on each.
There is no custom signal file — forwarding is handled inline in `index.js`.

## How func differs from the other sub-apps

- No explicit signal object wrapper (`{value}`, `{v,a}`, `{text}`) — raw string
- No named pip or multi-pip routing — single in/out only
- No gate logic
- State is per-panel via `storedValue` on the panel object, not a shared store

## Adding a new exec transform

1. Add a method to `ExecNodes` in `exec-nodes.js`.
2. Done — `execNodeNames` picks it up automatically.

## Adding a new value combine op

1. Add a method to `ValueNode` in `value-node.js`.
2. Done — `valueNodeOps` picks it up automatically.
