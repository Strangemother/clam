# Breaker

**Type key:** `breaker`  
**Group:** Control  
**File:** `static/js/power2/nodes/breaker.js`

## Description

The Breaker is a **manual switch with automatic over-current trip protection**. In normal operation it acts like a relay — passing the upstream signal through when closed, blocking it when open. If the incoming current exceeds `ratingAmps` the breaker trips automatically and must be manually reset by toggling it open before it can be closed again.

## Default Power Parameters

| Parameter      | Default | Description |
|----------------|---------|-------------|
| `ratingAmps`   | `16`    | Trip threshold in amps |
| `closed`       | `true`  | Manual closed/open state |
| `tripped`      | `false` | Auto-tripped on over-current |

Breakers have **one inbound pip** and **one outbound pip**.

## States

| State      | Meaning |
|------------|---------|
| `off`      | No upstream signal |
| `closed`   | Signal passes through normally |
| `open`     | Manually opened; signal blocked |
| `tripped`  | Over-current detected; signal blocked until the breaker is reset |

## Catalog Presets

| Key           | Label       | ratingAmps |
|---------------|-------------|------------|
| `breaker-6a`  | Breaker 6A  | 6          |
| `breaker-13a` | Breaker 13A | 13         |
| `breaker-30a` | Breaker 30A | 30         |
| `relay`       | Relay       | 10         |

## Events Emitted

| Event            | Payload                                    | When |
|------------------|--------------------------------------------|------|
| `state:change`   | `{ from, to }`                             | Any state transition |
| `breaker:tripped`| `{ amps, ratingAmps }`                     | Over-current trip |
| `breaker:toggle` | `{ closed, tripped }`                      | Manual toggle |
| `breaker:reset`  | `{}`                                       | Full reset |

## Trip and Reset Behaviour

1. **Normal flow** — upstream amps ≤ `ratingAmps`: signal passes as-is.
2. **Over-current** — upstream amps > `ratingAmps`: `tripped = true`, signal blocked.
3. **Resetting a trip** — call `toggle()` once. This sets `tripped = false` and `closed = false` (open position). A second `toggle()` closes it and resumes flow.

## Actions

```js
Breaker.toggle(panel, graph)
// If tripped: resets to open. If closed: opens. If open: closes.

Breaker.reset(panel, graph)
// Full reset: clears trip, closes the breaker, clears power-source tracking.
```

## Implementation Example

```js
const panel = graph.addPreset('breaker-13a')

// Listen for trips
panel.addEventListener('breaker:tripped', e => {
    console.warn(`Tripped at ${e.detail.amps} A (rated ${e.detail.ratingAmps} A)`)
})

// Manually open and re-close
Breaker.toggle(panel, graph)   // open
Breaker.toggle(panel, graph)   // close
```

## Subclassing

```js
class MagneticBreaker extends Breaker {
    static type        = 'mag-breaker'
    static label       = 'Magnetic Breaker'
    static catalog = [
        { key: 'mag-63a', label: 'Mag 63A', ratingAmps: 63 },
    ]
}
NodeRegistry.register(MagneticBreaker)
```
