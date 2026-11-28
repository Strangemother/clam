# Decision Node

**Type key:** `decision`  
**Group:** Control  
**File:** `static/js/power2/nodes/decision.js`

## Description

The Decision Node is a **programmable router**. It evaluates a `decide()` function on every signal arrival and on a configurable tick interval, then forwards the inbound signal to one output, multiple outputs (multicast), or blocks it entirely (null).

There are two ways to define routing logic:

1. **Subclass** `DecisionNode` and override the static `decide()` method — ideal for reusable, named routing rules.
2. **Runtime callback** — set `panel.decideCallback` on any `decision` node at runtime — ideal for one-off dynamic rules.

## Default Power Parameters

The Decision Node imposes no wattage draw of its own. Its power budget is purely structural — it routes whatever signal arrives.

| Parameter      | Default | Description |
|----------------|---------|-------------|
| `outputCount`  | `2`     | Number of outbound output pips |
| `inputCount`   | `2`     | Number of inbound input pips |
| `tickInterval` | `1.0`   | Seconds between tick-driven re-evaluations |
| `defaultOutput`| `0`     | Fallback output index if `decide()` returns `undefined` |

## States

| State      | Meaning |
|------------|---------|
| `off`      | No active signal |
| `routing`  | Signal present; routing to one or more outputs |
| `blocked`  | `decide()` returned `null`; signal suppressed on all outputs |
| `error`    | Internal routing fault |

## Catalog Presets

| Key             | Label                    | inputCount | outputCount |
|-----------------|--------------------------|------------|-------------|
| `decision-2`    | Decision (2 in → 2 out)  | 2          | 2           |
| `decision-2-3`  | Decision (2 in → 3 out)  | 2          | 3           |
| `decision-4`    | Decision (4 in → 4 out)  | 4          | 4           |

## Events Emitted

| Event           | Payload                                     | When |
|-----------------|---------------------------------------------|------|
| `state:change`  | `{ from, to }`                              | State transition |
| `decision:route`| `{ output, inPip, signal }`                 | Signal routed to an output |
| `decision:block`| `{ inPip }`                                 | Signal blocked (decide returned null) |
| `decision:reset`| `{}`                                        | Reset called |

## `decide()` Return Values

| Return value | Effect |
|---|---|
| `number` (index) | Route signal to that single output |
| `number[]` | Multicast to all listed output indices |
| `null` | Block signal on all outputs |
| `undefined` | Falls back to `defaultOutput` |

## Per-pip Signal Tracking

When multiple inbound pips are present, the last signal received on each pip is stored in `panel._pipSignals[pipIndex]`. The `decide()` call receives the most recently changed pip's signal and the panel, so routing rules can inspect all active inputs:

```js
static decide(panel, signal) {
    const pip0 = panel._pipSignals[0]
    const pip1 = panel._pipSignals[1]
    if (!pip0 && !pip1) return null
    return pip0?.v > pip1?.v ? 0 : 1   // forward the higher-voltage source
}
```

## Routing via Subclass

```js
class VoltageRouter extends DecisionNode {
    static type        = 'volt-router'
    static label       = 'Voltage Router'
    static outputCount = 3

    static defaults(id, preset = {}) {
        return { ...super.defaults(id, preset), minVolt: preset.minVolt ?? 180 }
    }

    static decide(panel, signal) {
        if (!signal) return null
        if (signal.v >= 200) return 0
        if (signal.v >= panel.minVolt) return 1
        return 2
    }
}
NodeRegistry.register(VoltageRouter)
```

## Routing via Runtime Callback

```js
const panel = graph.addType('decision')

panel.decideCallback = (signal, panel) => {
    if (!signal) return null
    return signal.v > 150 ? 0 : 1
}
```

## Tick-driven Re-evaluation

`tickInterval` controls how often the decision is re-evaluated even when the inbound signal has not changed. This is useful for time-based routing (e.g. switching to a backup output after 10 s of low voltage):

```js
// Check once per second by default
panel.tickInterval = 0.5   // check every 500 ms instead
```

## Actions

```js
DecisionNode.reset(panel, graph)
// Clears lastDecision, tick accumulator, pip signal cache, then delegates
// to NodeBase.reset().
```

## Implementation Example

```js
// A simple A/B failover: normally route to output 0; switch to output 1 if voltage sags
class FailoverRouter extends DecisionNode {
    static type        = 'failover'
    static label       = 'Failover'
    static outputCount = 2

    static decide(panel, signal) {
        if (!signal || signal.v < 200) return 1   // backup
        return 0                                   // main
    }
}
NodeRegistry.register(FailoverRouter)

const panel = graph.addType('failover')
panel.addEventListener('decision:route', e => {
    console.log(`Routing to output ${e.detail.output}`)
})
```
