# Series Battery

**Type key:** `series-bat`  
**Group:** Source  
**File:** `static/js/power2/nodes/series-battery.js`

## Description

The Series Battery is a **rechargeable energy store** with both an inbound (charging) pip and an outbound (source) pip. It operates independently of upstream voltage: when live, it **adds its own rated EMF** on top of the inbound voltage before forwarding downstream, modelling a battery in series with the supply.

Charging and discharging are computed independently each tick. If the battery runs out of charge it enters `dead` state and can only revive once it has accumulated at least 1 % capacity from a connected charger.

A **pass-through mode** (`live = false`) forwards the inbound signal unchanged — useful for bridging without boosting.

## Default Power Parameters

| Parameter       | Default | Description |
|-----------------|---------|-------------|
| `volts`         | `12`    | Rated output EMF added to inbound voltage |
| `amps`          | `20`    | Maximum output current |
| `chargeAmps`    | `10`    | Maximum inbound charge current accepted |
| `capacityWh`    | `10`    | Total energy capacity in watt-hours |
| `chargeWh`      | `= capacityWh` | Current stored energy (starts full) |
| `live`          | `true`  | Output enabled; false = pass-through mode |

## States

| State          | Meaning |
|----------------|---------|
| `off`          | No inbound signal and `live = false` |
| `pass`         | `live = false`; inbound signal forwarded unchanged |
| `charging`     | `live = true`; charge level rising |
| `discharging`  | `live = true`; charge level falling |
| `full`         | `live = true`; fully charged |
| `dead`         | Charge exhausted; no output until revived by charger |

## Catalog Presets

| Key             | Label               | volts | amps | chargeAmps | capacityWh |
|-----------------|---------------------|-------|------|------------|------------|
| `series-12v`    | Battery 12V 10Ah    | 12    | 20   | 10         | 120        |
| `series-24v`    | Battery 24V 10Ah    | 24    | 20   | 10         | 240        |
| `series-48v`    | Battery 48V 20Ah    | 48    | 30   | 15         | 960        |
| `series-lipo`   | LiPo 3.7V 5Ah       | 3.7   | 10   | 5          | 18.5       |
| `series-9v`     | PP3 9V 0.5Ah        | 9     | 1    | 0.5        | 4.5        |
| `series-super`  | Supercap 12V 0.1Wh  | 12    | 50   | 50         | 0.1        |

## Live Readings

| Field           | Type   | Description |
|-----------------|--------|-------------|
| `chargePercent` | number | 0–100 charge level |
| `chargeInW`     | number | Live inbound charge power (W) |
| `chargeOutW`    | number | Live outbound draw power (W) |
| `inVolts`       | number | Inbound voltage readout |
| `inAmps`        | number | Inbound current readout |

## Energy Model

Each tick:

```
chargeInW  = min(A_in, chargeAmps) × V_bat            (if inbound voltage > 0)
chargeOutW = drawWatts × V_bat / (V_in + V_bat)        (proportional share)
net (W)    = chargeInW − chargeOutW
ΔchargeWh  = net × dt / 3600
```

When standalone (`V_in = 0`) the denominator reduces correctly and `chargeOutW = drawWatts`.

## Events Emitted

| Event             | Payload                                             | When |
|-------------------|-----------------------------------------------------|------|
| `state:change`    | `{ from, to }`                                      | Any state transition |
| `battery:dead`    | `{ chargePercent: 0 }`                              | Charge exhausted |
| `battery:revived` | `{ chargePercent }`                                 | Auto-revival from charger |
| `battery:toggle`  | `{ live }`                                          | Toggle called |
| `battery:pass-toggle` | `{ live }`                                      | Pass-through toggled |
| `battery:charge`  | `{ chargePercent, chargeWh, chargeInW, chargeOutW }`| Charge level changes (throttled) |
| `battery:reset`   | `{ chargePercent: 100 }`                            | Reset called |

## Ripple & Spike

| Feature          | Default  |
|------------------|----------|
| `spike.enabled`  | `true`   |
| `spike.percent`  | `10 %`   |
| `spike.duration` | `0.3 s`  |
| `ripple.enabled` | `false`  |
| `ripple.amount`  | `0.5 V`  |
| `ripple.interval`| `0.5 s`  |

## Actions

```js
SeriesBattery.toggle(panel, graph)
// Toggle output on or off. No-op if dead. Starts inrush spike when enabling.

SeriesBattery.togglePass(panel, graph)
// Switch between boost mode (live=true) and pass-through mode (live=false).

SeriesBattery.paramsChanged(panel, graph)
// Validate and reapply after config changes (e.g. new capacityWh or chargeAmps).

SeriesBattery.reset(panel, graph)
// Restore to 100 % charge, re-enable output, clear all telemetry.
```

## Implementation Example

```js
// Add a 12V battery in series with a wall outlet to boost to 252V
const gen = graph.addPreset('wall-outlet')   // 240 V
const bat = graph.addPreset('series-12v')    // adds +12 V → 252 V downstream
const load = graph.addPreset('motor-sm')

graph.connect(gen, 0, bat, 0)
graph.connect(bat, 0, load, 0)

// Monitor charge
bat.addEventListener('battery:charge', e => {
    console.log(`Charge: ${e.detail.chargePercent.toFixed(1)} %`)
})

bat.addEventListener('battery:dead', () => {
    console.warn('Battery dead — needs charging')
})
```
