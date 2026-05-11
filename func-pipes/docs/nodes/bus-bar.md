# Bus Bar

**Type key:** `bus-bar`  
**Group:** Distribution  
**File:** `static/js/power2/nodes/bus-bar.js`

## Description

The Bus Bar is a **power distribution node**. It accepts a single inbound signal and splits it proportionally across N outbound output channels. Each channel receives a fraction of the total input current, determined by a per-channel **weight** value. Weights are automatically normalised so the split always adds up to 100 %, regardless of the raw numbers entered.

The Bus Bar extends `DecisionNode` but disables all routing logic — it distributes to *all* outputs simultaneously rather than choosing between them.

## Default Power Parameters

| Parameter      | Default              | Description |
|----------------|----------------------|-------------|
| `outputCount`  | `4`                  | Number of output channels |
| `inputCount`   | `1`                  | Always 1 inbound pip |
| `weights`      | Equal split          | Raw per-channel weights (e.g. `[25,25,25,25]`) |
| `_normWeights` | Auto-computed        | Normalised 0–1 fractions (internal) |

## States

| State      | Meaning |
|------------|---------|
| `off`      | Null input; all outputs silenced |
| `routing`  | Active; signal distributed across all channels |
| `error`    | Internal error (e.g. degenerate weight sum — extremely rare) |

## Catalog Presets

| Key         | Label           | outputCount |
|-------------|-----------------|-------------|
| `bus-bar-2` | Bus Bar (2 ch)  | 2           |
| `bus-bar-4` | Bus Bar (4 ch)  | 4           |
| `bus-bar-6` | Bus Bar (6 ch)  | 6           |
| `bus-bar-8` | Bus Bar (8 ch)  | 8           |

## Events Emitted

| Event                  | Payload                                     | When |
|------------------------|---------------------------------------------|------|
| `state:change`         | `{ from, to }`                              | Routing state changes |
| `busbar:weight-changed`| `{ index, weight, normWeights }`            | A single channel weight is updated |
| `busbar:equalised`     | `{ weights }`                               | `equalise()` called |
| `busbar:reset`         | `{ outputCount }`                           | Full reset |

## Weight Distribution

All weights are raw numbers in arbitrary units. The engine normalises them before distributing:

```
normWeight[i] = weight[i] / sum(all weights)
output[i].a   = input.a × normWeight[i]
output[i].v   = input.v           (voltage is not reduced)
```

**Example** — 3 channels, weights `[2, 1, 1]`:
- Channel 0 receives 50 % of input amps
- Channels 1 and 2 each receive 25 %

## Actions

```js
BusBar.setChannelWeight(panel, index, value, graph)
// Set one channel's weight. Other channels are unchanged; renormalisation is automatic.

BusBar.applyWeights(panel, graph)
// Re-normalise and re-emit after weights have been mutated in-place (e.g. via v-model).

BusBar.equalise(panel, graph)
// Reset all channels to an equal share.

BusBar.reset(panel, graph)
// Re-normalise weights and delegate to NodeBase.reset().
```

## Implementation Example

```js
const panel = graph.addPreset('bus-bar-4')

// Bias channel 0 to receive 60 % of power
BusBar.setChannelWeight(panel, 0, 60, graph)
BusBar.setChannelWeight(panel, 1, 20, graph)
BusBar.setChannelWeight(panel, 2, 10, graph)
BusBar.setChannelWeight(panel, 3, 10, graph)

// Restore equal distribution
BusBar.equalise(panel, graph)
```

## Subclassing Example

```js
class PowerRail extends BusBar {
    static type        = 'power-rail'
    static label       = 'Power Rail'
    static outputCount = 6
    static catalog = [
        { key: 'power-rail-6', label: 'Power Rail (6 ch)', outputCount: 6 },
    ]
}
NodeRegistry.register(PowerRail)
```
