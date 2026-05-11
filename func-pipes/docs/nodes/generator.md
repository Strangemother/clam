# Generator

**Type key:** `gen`  
**Group:** Source  
**File:** `static/js/power2/nodes/gen.js`

## Description

The Generator is the root **power source** of any circuit. It produces a fixed `{ v, a }` signal on its single outbound pip and has no inbound connection. Every powered sub-graph must start with at least one Generator.

An inrush spike is emitted each time the generator starts, modelling the brief surge seen when a real source energises a downstream network.

## Default Power Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `volts`   | `240`   | Output voltage (V) |
| `amps`    | `13`    | Rated maximum output current (A) |
| `live`    | `false` | Whether the generator is currently producing power |

Rated power = `volts × amps` (e.g. 240 V × 13 A = 3 120 W for the Wall Outlet preset).

## States

| State      | Meaning |
|------------|---------|
| `off`      | Generator is stopped; no signal emitted |
| `on`       | Normal operation; `{ v, a }` signal driven downstream |
| `sag`      | Overloaded 100–130 % of rating; voltage reduced to 85 % |
| `tripped`  | Overloaded > 130 % of rating; output cut; requires manual toggle to reset |

## Catalog Presets

| Key            | Label          | Volts | Amps  |
|----------------|----------------|-------|-------|
| `wall-outlet`  | Wall Outlet    | 240   | 13    |
| `gen-30a`      | Generator      | 240   | 30    |
| `ship-reactor` | Ship Reactor   | 240   | 120   |
| `battery-12v`  | Battery 12V    | 12    | 20    |
| `battery-48v`  | Battery 48V    | 48    | 30    |

## Events Emitted

| Event           | Payload                              | When |
|-----------------|--------------------------------------|------|
| `state:change`  | `{ from, to }`                       | Any state transition |
| `gen:start`     | `{ volts, amps }`                    | Generator turned on |
| `gen:stop`      | `{ volts, amps }`                    | Generator turned off |
| `gen:params`    | `{ volts, amps }`                    | Voltage or amps changed while live |
| `gen:overload`  | `{ drawAmps, ratedAmps }`            | Load exceeds rating (BFS pass) |
| `gen:reset`     | `{}`                                 | Generator reset |

## Overload Model

The BFS walk computes `drawWatts` / `drawAmps` across all downstream loads after each graph update. Generator state is then set according to the load fraction:

```
drawAmps / amps ≤ 1.0   →  on        (full output)
drawAmps / amps ≤ 1.3   →  sag       (85 % voltage)
drawAmps / amps  > 1.3   →  tripped   (null output, manual reset)
```

## Ripple & Spike

| Feature | Default |
|---------|---------|
| `ripple.enabled` | `false` |
| `ripple.amount`  | `2.0 V` |
| `ripple.interval`| `0.8 s` |
| `spike.enabled`  | `true`  |
| `spike.percent`  | `15 %`  |
| `spike.duration` | `0.94 s`|

## Actions

```js
Generator.toggle(panel, graph)
// Turns on or off. A tripped generator resets to 'off' on the first call.

Generator.paramsChanged(panel, graph)
// Call after editing panel.volts or panel.amps to re-emit the updated signal.

Generator.reset(panel, graph)
// Full reset: turns off, clears overload and draw telemetry.
```

## Implementation Example

```js
const panel = graph.addType('gen')          // default 240 V / 13 A
// or from catalog:
const panel = graph.addPreset('wall-outlet')

Generator.toggle(panel, graph)              // start producing power

// Listen for overload events
panel.addEventListener('gen:overload', e => {
    console.warn('Overload!', e.detail)
})
```
