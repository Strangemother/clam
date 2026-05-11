# Bulb

**Type key:** `bulb`  
**Group:** Light  
**File:** `static/js/power2/nodes/bulb.js`

## Description

The Bulb is a **visual power sink** — a resistive lamp that consumes all power reaching it and emits nothing downstream. It grades between three visual states based on the voltage and current it receives: fully off, dim (under-voltage / under-current), and fully lit. Overvoltage or overcurrent permanently blows the bulb until it is manually reset.

Because the Bulb is a sink, it has **one inbound pip** and **no outbound pip**.

## Default Power Parameters

| Parameter   | Default              | Description |
|-------------|----------------------|-------------|
| `watts`     | `60`                 | Rated wattage (determines amp draw) |
| `maxVolts`  | `volts × 1.2`        | Above this the bulb blows (overvoltage) |
| `maxAmps`   | `(watts / 240) × 2` | Above this the bulb blows (overcurrent) |
| `brightness`| `0`                  | 0.0–1.0 visual brightness (for CSS/animation) |
| `blown`     | `false`              | Permanently destroyed until reset |

## States

| State    | Meaning |
|----------|---------|
| `off`    | No signal or voltage too low (< 180 V) |
| `dim`    | Under-voltage or under-current; partial brightness |
| `on`     | Fully lit at rated brightness |
| `blown`  | Destroyed by overvoltage or overcurrent |

## Catalog Presets

| Key          | Label      | watts |
|--------------|------------|-------|
| `led-5w`     | LED 5W     | 5     |
| `bulb-40w`   | Bulb 40W   | 40    |
| `bulb-60w`   | Bulb 60W   | 60    |
| `bulb-100w`  | Bulb 100W  | 100   |

## Events Emitted

| Event           | Payload                                   | When |
|-----------------|-------------------------------------------|------|
| `state:change`  | `{ from, to }`                            | State transition |
| `bulb:blown`    | `{ reason, volts/amps, maxVolts/maxAmps }`| Destruction event |
| `bulb:brownout` | `{ volts, amps }`                         | Transitions into dim state |
| `bulb:brightness`| `{ brightness }`                         | Brightness changes by ≥ 0.05 |
| `bulb:reset`    | `{}`                                      | Reset called |

## Brightness Calculation

```
drawAmps  = watts / NOMINAL_VOLTS
voltRatio = signal.v / NOMINAL_VOLTS
ampRatio  = signal.a / drawAmps

if voltage < 180 V or amps < 5% of drawAmps  → off,  brightness = 0
if voltRatio < 0.9 or ampRatio < 1.0         → dim,  brightness ≤ 0.55
otherwise                                     → on,   brightness = min(1, voltRatio)
```

## Spike

The inrush spike models the filament's cold-resistance surge at turn-on:

| Feature          | Default  |
|------------------|----------|
| `spike.enabled`  | `true`   |
| `spike.percent`  | `25 %`   |
| `spike.duration` | `0.73 s` |

## Actions

```js
Bulb.reset(panel, graph)
// Clears the blown flag, resets brightness to 0, and propagates to NodeBase.reset().
// After reset, the bulb will light again when a valid signal arrives.
```

## Implementation Example

```js
const panel = graph.addPreset('bulb-60w')

// React to state changes
panel.addEventListener('state:change', e => {
    const el = document.getElementById('bulb-icon')
    el.className = `bulb bulb--${e.detail.to}`   // 'off' | 'dim' | 'on' | 'blown'
})

// Animate brightness continuously
panel.addEventListener('bulb:brightness', e => {
    document.getElementById('bulb-icon').style.opacity = e.detail.brightness
})

// Handle blown bulb
panel.addEventListener('bulb:blown', e => {
    console.error(`Bulb blown: ${e.detail.reason}`)
    // Allow user to reset:
    Bulb.reset(panel, graph)
})
```
