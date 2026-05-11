# Meter

**Type key:** `meter`  
**Group:** Instrument  
**File:** `static/js/power2/nodes/meter.js`

## Description

The Meter is a **transparent, read-only power instrument**. It measures voltage (V), current (A), and computed power (W) from the inbound signal and then passes that signal through to downstream nodes completely unchanged. It has one inbound pip and one outbound pip.

The Meter imposes no load and alters no values — it is purely observational. Use it anywhere in a circuit where you need a live power reading without interrupting the flow.

## Default Power Parameters

The Meter introduces no power requirement of its own. All measurements are derived from the signal passing through it.

| Field   | Type   | Description |
|---------|--------|-------------|
| `volts` | number | Measured voltage (V) |
| `amps`  | number | Measured current (A) |
| `watts` | number | Computed power: `volts × amps` (W) |

## States

| State | Meaning |
|-------|---------|
| `off` | No upstream signal |
| `on`  | Signal present and being measured |

## Catalog Presets

| Key     | Label       |
|---------|-------------|
| `meter` | Power Meter |

## Events Emitted

| Event           | Payload                       | When |
|-----------------|-------------------------------|------|
| `state:change`  | `{ from, to }`                | State transitions on/off |
| `meter:reading` | `{ volts, amps, watts }`      | V or A changes (throttled) |
| `meter:reset`   | `{}`                          | Reset called |

Readings are **throttled** — the `meter:reading` event is only dispatched when the measured voltage or current differs from the previous reading. This prevents event storms when values are stable.

## Actions

```js
Meter.reset(panel, graph)
// Zero all readings, clear de-dupe tracking, and propagate to NodeBase.reset().
```

## Implementation Example

```js
// Place a meter between a generator and a breaker to monitor supply
const gen     = graph.addPreset('wall-outlet')
const meter   = graph.addType('meter')
const breaker = graph.addPreset('breaker-13a')

graph.connect(gen, 0, meter, 0)
graph.connect(meter, 0, breaker, 0)

// Display live readings
meter.addEventListener('meter:reading', e => {
    const { volts, amps, watts } = e.detail
    document.getElementById('power-display').textContent =
        `${volts} V  ${amps} A  ${watts} W`
})
```

## Notes

- The Meter is the preferred way to observe power values mid-circuit without affecting the simulation.
- For logging or recording readings over time, subscribe to `meter:reading` and accumulate values in your own store.
- Multiple meters can be chained without affecting each other or the signal.
