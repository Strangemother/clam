# Converter

**Type key:** `converter`  
**Group:** Converter  
**File:** `static/js/power2/nodes/converter.js`

## Description

The Converter is a **step-up / step-down transformer** (or DC-DC converter). It scales voltage up or down to a configurable target while accounting for I²R losses via an `efficiency` factor. It has one inbound and one outbound pip.

On the **first live signal** the converter snapshots the input voltage to define its *turns ratio*. All subsequent frames track that ratio so voltage ripple from upstream passes through. Calling `dialUp()`, `dialDown()`, or `paramsChanged()` re-locks the ratio to the current input.

## Default Power Parameters

| Parameter      | Default | Description |
|----------------|---------|-------------|
| `outVolts`     | `120`   | Target output voltage (V) |
| `step`         | `10`    | Dial increment in volts |
| `efficiency`   | `0.95`  | Power transfer factor (0–1; 1 = lossless) |

### Physics

```
turns ratio  = outVolts / _baseInVolts
P_in         = V_in × A_in
P_out        = P_in × efficiency
V_out        = V_in × turns_ratio      (ripple passes through)
A_out        = P_out / V_out
```

## States

| State       | Meaning |
|-------------|---------|
| `off`       | No valid input signal |
| `step-up`   | V_out > V_in (ratio > 1.005) |
| `step-down` | V_out < V_in (ratio < 0.995) |
| `unity`     | V_out ≈ V_in (near-1:1 ratio) |
| `fault`     | Computed V_out or A_out ≤ 0 (e.g. zero-efficiency edge case) |

## Catalog Presets

| Key          | Label               | outVolts | efficiency |
|--------------|---------------------|----------|------------|
| `conv-480v`  | Step-up 240→480V   | 480      | 0.95       |
| `conv-24v`   | Step-down 240→24V  | 24       | 0.95       |
| `conv-12v`   | Step-down 240→12V  | 12       | 0.95       |
| `conv-5v`    | Step-down 240→5V   | 5        | 0.95       |
| `psu-atx`    | ATX PSU (12V)       | 12       | 0.88       |

## Events Emitted

| Event                | Payload                                                  | When |
|----------------------|----------------------------------------------------------|------|
| `state:change`       | `{ from, to }`                                           | State transition |
| `converter:reading`  | `{ inVolts, inAmps, outVolts, outAmps, ratio }`          | V or A changes (throttled) |
| `converter:fault`    | `{ inVolts, inAmps }`                                   | Computed output is zero |
| `converter:dial`     | `{ outVolts, direction }`                               | Dial adjusted |
| `converter:params`   | `{ outVolts, efficiency }`                              | Params changed |
| `converter:reset`    | `{}`                                                    | Reset |

## Live Readings

The converter exposes these fields on its panel in real time:

| Field      | Type   | Description |
|------------|--------|-------------|
| `inVolts`  | number | Last measured input voltage |
| `inAmps`   | number | Last measured input current |
| `outAmps`  | number | Computed output current |
| `ratio`    | number | Live V_out / V_in ratio |

## Actions

```js
Converter.dialUp(panel, graph)
// Increase outVolts by panel.step and re-lock the turns ratio.

Converter.dialDown(panel, graph)
// Decrease outVolts by panel.step (minimum 1 V) and re-lock the turns ratio.

Converter.paramsChanged(panel, graph)
// Validate and reapply after external edits to outVolts, step, or efficiency.

Converter.reset(panel, graph)
// Clear all measurements and the locked turns-ratio snapshot.
```

## Ripple

| Feature          | Default  |
|------------------|----------|
| `ripple.enabled` | `false`  |
| `ripple.amount`  | `1.0 V`  |
| `ripple.interval`| `1.2 s`  |

Upstream ripple passes through automatically because V_out tracks V_in via the turns ratio.

## Implementation Example

```js
// Step down mains 240 V to 12 V for downstream low-voltage loads
const panel = graph.addPreset('conv-12v')

// Dial the target output up to 13.8 V (charging voltage)
Converter.dialUp(panel, graph)   // 12 + 10 = 22 V — or set step first:
panel.step = 1.8
Converter.dialUp(panel, graph)   // → 13.8 V

// Monitor the conversion
panel.addEventListener('converter:reading', e => {
    const { inVolts, outVolts, ratio } = e.detail
    console.log(`${inVolts} V → ${outVolts} V  (ratio ${ratio})`)
})
```
