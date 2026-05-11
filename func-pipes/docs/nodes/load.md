# Load

**Type key:** `load`  
**Group:** Load  
**File:** `static/js/power2/nodes/load.js`

## Description

The Load is the **generic configurable power consumer**. It draws a set wattage from the upstream circuit, subtracts its amp draw from the signal, and passes any remaining current downstream. It supports:

- **Brownout detection** — goes offline if voltage falls below `minVolts`.
- **Overvoltage protection** — permanently blows if voltage exceeds `maxVolts`.
- **Capacitor buffer** — an optional watt-second store that keeps the load alive for a short window after power is lost.
- **Noise** — a sine-wave draw oscillation that simulates realistic current variation.
- **Inrush spike** — a brief over-current pulse at startup.

Load is also the **base class** for `Heater` and `ConsoleNode`. Extend it to create custom equipment types.

## Default Power Parameters

| Parameter      | Default | Description |
|----------------|---------|-------------|
| `watts`        | `100`   | Rated wattage draw |
| `currentWatts` | `watts` | Live effective draw (modulated by noise and spike) |
| `minVolts`     | `200`   | Minimum operating voltage |
| `maxVolts`     | `300`   | Overvoltage destruction threshold |
| `capacitance`  | `0`     | Buffer size in watt-seconds (0 = no capacitor) |
| `blown`        | `false` | Permanently destroyed flag |

## States

| State        | Meaning |
|--------------|---------|
| `off`        | No upstream signal |
| `on`         | Powered and operating normally |
| `brownout`   | Voltage present but below `minVolts`; load offline |
| `capacitor`  | Grid power lost; running on internal capacitor buffer |
| `blown`      | Destroyed by overvoltage; requires manual reset |

## Catalog Presets

| Key        | Label       | watts  | minVolts | capacitance |
|------------|-------------|--------|----------|-------------|
| `fan`      | Fan         | 25     | 200      | 0           |
| `pump`     | Pump        | 180    | 210      | 0           |
| `motor-sm` | Motor (sm)  | 370    | 215      | 0           |
| `motor-lg` | Motor (lg)  | 1500   | 220      | 0           |
| `ups`      | UPS Buffer  | 5      | 190      | 600 Ws      |

## Events Emitted

| Event                       | Payload                                         | When |
|-----------------------------|-------------------------------------------------|------|
| `state:change`              | `{ from, to }`                                  | Any state transition |
| `load:blown`                | `{ volts, maxVolts }`                           | Overvoltage destruction |
| `load:brownout`             | `{ volts, amps, minVolts }`                    | Voltage drops below minimum |
| `load:capacitor-failover`   | `{ chargeWs }`                                  | Grid lost; capacitor engaged |

## Capacitor Buffer

When `capacitance > 0` the load maintains an internal energy reserve in watt-seconds:

- **Charging** — while `state === 'on'` the buffer charges at `watts × dt` per tick.
- **Running on cap** — when grid power is lost and `chargeWs > 0` the state becomes `capacitor`.
- **Exhausted** — when `chargeWs` reaches 0 the state transitions to `off`.

```js
// UPS-style buffer: 600 Ws ÷ 5 W = 120 s of hold-up time
const panel = graph.addPreset('ups')

// Query current charge
const pct = Load.chargePercent(panel)   // 0–100
```

## Noise

The noise feature applies a slow sine-wave modulation to the effective draw:

```js
noise: {
    enabled: true,
    period:  2.0,    // seconds per oscillation cycle
    amount:  0.10,   // ±10 % of rated watts
}
```

## Ripple & Spike

| Feature          | Default  |
|------------------|----------|
| `spike.enabled`  | `true`   |
| `spike.percent`  | `20 %`   |
| `spike.duration` | `0.95 s` |
| `ripple.enabled` | `false`  |

## Actions

```js
Load.paramsChanged(panel, graph)
// Re-evaluate signal after external config changes. Routes through the
// NodeRegistry so subclasses use their own apply() method.

Load.chargePercent(panel)
// Returns 0–100 cap charge level. Returns 0 if no capacitor fitted.

Load.reset(panel, graph)
// Clears blown flag, resets capacitor charge, clears power-source tracking.
```

## Implementation Example

```js
const panel = graph.addPreset('motor-sm')

panel.addEventListener('load:brownout', e => {
    console.warn('Motor brownout', e.detail)
})

panel.addEventListener('state:change', e => {
    if (e.detail.to === 'on') console.log('Motor running')
    if (e.detail.to === 'off') console.log('Motor stopped')
})
```

## Subclassing

```js
class AirConditioner extends Load {
    static type  = 'air-con'
    static label = 'Air Conditioner'
    static group = 'Appliance'
    static catalog = [
        { key: 'ac-1500w', label: 'AC 1500W', watts: 1500, minVolts: 210 },
    ]
}
NodeRegistry.register(AirConditioner)
```
