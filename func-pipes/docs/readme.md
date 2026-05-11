# Power2 Node Reference

This document is the index for the **power2** graph node system — a modular, event-driven electrical simulation built on plain reactive objects and static class behaviour.

Each node represents a physical electrical component. Nodes are connected via **pips** (connection points) and communicate through a directed **signal** of `{ v: volts, a: amps }`.

---

## Node Index

| Node | Type Key | Group | Description |
|------|----------|-------|-------------|
| [Generator](nodes/generator.md) | `gen` | Source | Root power source; produces a fixed voltage/current signal |
| [Series Battery](nodes/series-battery.md) | `series-bat` | Source | Rechargeable battery; adds own EMF in series with the supply |
| [Breaker](nodes/breaker.md) | `breaker` | Control | Manual switch with automatic over-current trip protection |
| [Decision Node](nodes/decision.md) | `decision` | Control | Programmable signal router with per-tick re-evaluation |
| [Bus Bar](nodes/bus-bar.md) | `bus-bar` | Distribution | Splits one input across N outputs with configurable weighting |
| [Converter](nodes/converter.md) | `converter` | Converter | Step-up / step-down transformer with configurable efficiency |
| [Meter](nodes/meter.md) | `meter` | Instrument | Transparent V/A/W instrument; passes signal through unchanged |
| [Load](nodes/load.md) | `load` | Load | Generic power consumer; base class for Heater and ConsoleNode |
| [Heater](nodes/heater.md) | `heater` | Appliance | Load with thermal simulation, thermostat, and dynamic draw |
| [Console Node](nodes/console.md) | `console` | Equipment | Load with boot sequence, shutdown countdown, and cap buffer |
| [Bulb](nodes/bulb.md) | `bulb` | Light | Visual power sink; brightness grades off / dim / on; no outbound pip |

---

## Core Concepts

### Signal Format

Every connection carries a signal object or null:

```js
{ v: 240, a: 13 }   // 240 V, 13 A
null                 // no power
```

### Pips

Each node exposes **inbound** and **outbound** pips. Pips are the physical connection points:

- `pipsInbound`  — where the node receives power from upstream
- `pipsOutbound` — where the node emits power to downstream nodes

Nodes with multiple inputs or outputs (e.g. Bus Bar, Decision) have indexed pips.

### Node Lifecycle

Every node class exposes three static hooks the graph engine calls automatically:

| Method | Called when |
|--------|-------------|
| `apply(panel, signal, graph)` | An upstream pip value changes |
| `tick(panel, dt, graph)` | Every animation frame (dt = elapsed seconds) |
| `reset(panel, graph)` | The graph or node is reset |

### Inrush Spike

Many nodes model an **inrush current spike** at startup — a brief burst of over-current that decays linearly over `spike.duration` seconds. The spike multiplier scales both voltage and amps during this window.

### Ripple

Nodes can emit a periodic voltage oscillation via the `ripple` configuration. Ripple is additive and passes through passive nodes (Meter, Breaker when closed, Converter).

---

## Inheritance Hierarchy

```
NodeBase
├── Generator
├── Meter
├── Breaker
├── Converter
├── SeriesBattery
├── DecisionNode
│   └── BusBar
└── Load
    ├── Heater
    ├── ConsoleNode
    └── Bulb  (sink — no outbound pip)
```

---

## Creating a Custom Node

1. Extend `NodeBase` (or a suitable subclass such as `Load`).
2. Declare `static type`, `label`, `group`, and `catalog`.
3. Override `static defaults(id, preset)` — call `super.defaults()` first.
4. Override `static apply(panel, signal, graph)` for your signal logic.
5. Optionally override `static tick(panel, dt, graph)` for per-frame behaviour.
6. Optionally override `static reset(panel, graph)`.
7. Call `NodeRegistry.register(YourClass)` at the bottom of your file.
8. Load your file in the HTML before `index.js`.

See [Heater](nodes/heater.md) and [Decision Node](nodes/decision.md) for worked subclassing examples.

---

## Quick Reference — Common Events

| Event | Emitted by | Meaning |
|-------|-----------|---------|
| `state:change` | All nodes | Any state transition |
| `gen:start` / `gen:stop` | Generator | Output toggled |
| `gen:overload` | Generator | Load exceeds rating |
| `breaker:tripped` | Breaker | Over-current trip |
| `busbar:weight-changed` | Bus Bar | Channel weight updated |
| `converter:reading` | Converter | V/A measured (throttled) |
| `meter:reading` | Meter | V/A measured (throttled) |
| `load:blown` | Load, Heater, Console | Overvoltage destruction |
| `load:brownout` | Load, Heater, Console | Under-voltage |
| `load:capacitor-failover` | Load, Heater, Console | Cap buffer engaged |
| `thermostat:trip` | Heater | Element cut at maxTemp |
| `thermostat:reset` | Heater | Element re-enabled |
| `heater:temperature` | Heater | Temperature change (throttled) |
| `console:boot-state` | ConsoleNode | Boot phase transition |
| `console:boot-progress` | ConsoleNode | Boot/shutdown progress |
| `bulb:blown` | Bulb | Overvoltage / overcurrent |
| `bulb:brightness` | Bulb | Brightness changes by ≥ 5 % |
| `battery:charge` | SeriesBattery | Charge level changes (throttled) |
| `battery:dead` | SeriesBattery | Charge exhausted |
| `battery:revived` | SeriesBattery | Auto-revived from charger |
