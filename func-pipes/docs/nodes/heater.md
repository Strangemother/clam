# Heater

**Type key:** `heater`  
**Group:** Appliance  
**File:** `static/js/power2/nodes/heater.js`

## Description

The Heater extends `Load` with a **thermal simulation and a built-in thermostat**. As it warms up its heating element draws progressively more power — from a standby minimum (`minWatts`) up to its full rated wattage. A thermostat (`heatSwitch`) cuts the element off at `maxTemp` and allows it to restart once the unit cools to `resetTemp`.

The Heater is the canonical example of a **custom node type** in this system — see the subclassing notes in `heater.js` for a step-by-step guide.

## Default Power Parameters

| Parameter      | Default | Description |
|----------------|---------|-------------|
| `watts`        | `1000`  | Rated element wattage (fully hot) |
| `minWatts`     | `50`    | Standby draw, always present even when element is tripped |
| `minVolts`     | `200`   | Minimum operating voltage |
| `maxVolts`     | `300`   | Overvoltage destruction threshold |
| `capacitance`  | `0`     | Watt-second buffer (inherited from Load) |

## Thermal Controls

| Parameter    | Default | Description |
|--------------|---------|-------------|
| `heatRate`   | `8`     | °C per second while element is on |
| `coolRate`   | `3`     | °C per second while element is off |
| `maxTemp`    | `100`   | Thermostat trip temperature (°C) |
| `resetTemp`  | `70`    | Thermostat reset temperature (°C) |

## States

Inherited from `Load`:

| State       | Meaning |
|-------------|---------|
| `off`       | No upstream signal |
| `on`        | Powered and heating |
| `brownout`  | Voltage below `minVolts` |
| `capacitor` | Running on internal buffer |
| `blown`     | Destroyed by overvoltage |

## Thermal State (`heatState`)

| Value     | Condition |
|-----------|-----------|
| `cold`    | Temperature < 20 % of `maxTemp` |
| `warming` | Temperature 20–60 % of `maxTemp` |
| `hot`     | Temperature > 60 % of `maxTemp` |

## Catalog Presets

| Key           | Label        | watts  | minVolts | Spike |
|---------------|--------------|--------|----------|-------|
| `heater-1kw`  | Heater 1 kW  | 1 000  | 200      | 30 % / 0.8 s |
| `heater-2kw`  | Heater 2 kW  | 2 000  | 205      | 35 % / 0.9 s |
| `heater-3kw`  | Heater 3 kW  | 3 000  | 210      | 40 % / 1.0 s |
| `heater-oil`  | Oil Heater   | 1 500  | 200      | 15 % / 0.5 s |

## Events Emitted

| Event                       | Payload                                      | When |
|-----------------------------|----------------------------------------------|------|
| `state:change`              | `{ from, to }`                               | Power state transition |
| `heater:blown`              | `{ volts, maxVolts }`                        | Overvoltage destruction |
| `heater:brownout`           | `{ volts, amps, minVolts }`                 | Under-voltage |
| `heater:capacitor-failover` | `{ chargeWs }`                               | Cap engaged on power loss |
| `thermostat:trip`           | `{ temp }`                                   | Element cut at `maxTemp` |
| `thermostat:reset`          | `{ temp }`                                   | Element re-enabled at `resetTemp` |
| `heater:temperature`        | `{ temp, max }`                              | Temperature change (throttled) |
| `heater:heat-state`         | `{ from, to, temp }`                         | Transitions cold/warming/hot |
| `heater:draw-change`        | `{ from, to }`                               | Draw changed by > 1 W |
| `heater:reset`              | `{}`                                         | Reset called |

## Dynamic Draw Model

```
elementWatts = minWatts + (watts - minWatts) × (temperature / maxTemp)
currentWatts = heatSwitch ? elementWatts : minWatts
```

The draw ramps linearly from `minWatts` when cold to `watts` when fully hot. The thermostat keeps the element cycling, so draw oscillates between `minWatts` and `watts` in steady operation.

## Spike

| Feature          | Default  |
|------------------|----------|
| `spike.enabled`  | `true`   |
| `spike.percent`  | `30 %`   |
| `spike.duration` | `3.8 s`  |

The large spike models the inrush current of a cold resistive element.

## Actions

```js
// (All Load actions are inherited)
Heater.reset(panel, graph)
// Zeros temperature, resets thermostat (heatSwitch = true), restores currentWatts
// to minWatts, then delegates to Load.reset().
```

## Implementation Example

```js
const panel = graph.addPreset('heater-2kw')

// Monitor thermostat cycling
panel.addEventListener('thermostat:trip',  e => console.log('Element OFF at', e.detail.temp, '°C'))
panel.addEventListener('thermostat:reset', e => console.log('Element ON  at', e.detail.temp, '°C'))

// Live temperature readout
panel.addEventListener('heater:temperature', e => {
    document.getElementById('temp').textContent = `${e.detail.temp} °C`
})
```
