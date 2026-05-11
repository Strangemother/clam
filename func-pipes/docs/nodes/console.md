# Console Node

**Type key:** `console`  
**Group:** Equipment  
**File:** `static/js/power2/nodes/console-node.js`

## Description

The Console Node extends `Load` with a **multi-stage boot simulation**. When power is applied it takes a configurable number of seconds to boot before reaching the `ready` state. When power is removed it gracefully shuts down over a configurable window. A capacitor buffer (if configured) allows a clean shutdown window after power loss.

This node demonstrates how to build a time-driven state machine on top of `Load`.

## Default Power Parameters

| Parameter          | Default | Description |
|--------------------|---------|-------------|
| `watts`            | `50`    | Rated wattage at full operation |
| `minVolts`         | `180`   | Minimum operating voltage |
| `maxVolts`         | `300`   | Overvoltage destruction threshold |
| `capacitance`      | `20`    | Watt-second buffer (keeps it alive during brief outages) |
| `bootDuration`     | `5`     | Seconds to fully boot |
| `shutdownDuration` | `2`     | Seconds to gracefully shut down |

## Boot State (`bootState`)

| Value      | Meaning |
|------------|---------|
| `off`      | No power; system not running |
| `booting`  | Power present; progressing through boot sequence |
| `ready`    | Fully booted and operational |
| `shutdown` | Power lost; executing graceful shutdown |

`bootProgress` (0–100) tracks how far through the current `booting` or `shutdown` phase the console is.

## Power States

Inherited from `Load`:

| State       | Meaning |
|-------------|---------|
| `off`       | No upstream signal |
| `on`        | Powered |
| `brownout`  | Under-voltage |
| `capacitor` | Running on buffer |
| `blown`     | Destroyed by overvoltage |

## Catalog Presets

| Key            | Label          | watts | minVolts | capacitance |
|----------------|----------------|-------|----------|-------------|
| `console-sm`   | Console (SM)   | 30    | 180      | 10 Ws       |
| `console-lg`   | Console (LG)   | 80    | 180      | 20 Ws       |
| `server-rack`  | Server Rack    | 500   | 200      | 50 Ws       |
| `workstation`  | Workstation    | 250   | 190      | 30 Ws       |

## Events Emitted

| Event                    | Payload                            | When |
|--------------------------|------------------------------------|------|
| `state:change`           | `{ from, to }`                     | Power state transition |
| `load:blown`             | `{ volts, maxVolts }`              | Overvoltage |
| `load:brownout`          | `{ volts, amps, minVolts }`       | Under-voltage |
| `load:capacitor-failover`| `{ chargeWs }`                    | Cap engaged |
| `console:boot-state`     | `{ from, to }`                     | Boot state machine transition |
| `console:boot-progress`  | `{ bootState, progress }`          | Boot/shutdown progress (throttled) |
| `console:reset`          | `{}`                               | Reset called |

## Dynamic Power Draw Model

```
booting   → draw ramps 0 → watts  proportional to bootProgress
ready     → draw oscillates 90–100 % of watts (20 s sine period, ±10 %)
shutdown  → draw ramps current → 0  as shutdown progresses
off       → 0 W
```

An inrush spike starts the moment boot begins.

## Spike

| Feature          | Default  |
|------------------|----------|
| `spike.enabled`  | `true`   |
| `spike.percent`  | `4 %`    |
| `spike.duration` | `2.0 s`  |

## Actions

All `Load` actions apply. Additional:

```js
ConsoleNode.reset(panel, graph)
// Returns to 'off' boot state, zeroes progress and dynamic-draw accumulators,
// then delegates to Load.reset().
```

## Implementation Example

```js
const panel = graph.addPreset('workstation')

// Track boot sequence
panel.addEventListener('console:boot-state', e => {
    console.log(`Boot state: ${e.detail.from} → ${e.detail.to}`)
})

panel.addEventListener('console:boot-progress', e => {
    const bar = document.getElementById('boot-bar')
    bar.style.width = `${e.detail.progress}%`
    bar.dataset.state = e.detail.bootState
})

// Handle cap failover (power blip — console survives if cap holds long enough)
panel.addEventListener('load:capacitor-failover', e => {
    console.warn(`Running on cap. ${e.detail.chargeWs.toFixed(0)} Ws remaining`)
})
```
