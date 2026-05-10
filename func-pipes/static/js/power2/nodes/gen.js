/*
  nodes/gen.js — Generator
  ─────────────────────────────────────────────────────────────────────────────
  A power source. Produces { v, a } when live. No inbound pip.

  Extended state
  ──────────────
  live      bool    — whether the generator is currently producing power
  overload  bool    — true when draw exceeded rating at last BFS pass
  drawWatts number  — total load watts served (computed by BFS)
  drawAmps  number  — equivalent amp draw at output voltage

  States: 'off' | 'on' | 'sag' | 'tripped'

  Overload model (proportion of rated amps)
  ──────────────────────────────────────────
    ≤ 1.0   — nominal  — full rated signal
    1.0–1.3 — sag      — voltage reduced to 85 %
    > 1.3   — tripped  — output cut, generator must be manually reset
*/

class Generator extends NodeBase {

    static type  = 'gen'
    static label = 'Generator'
    static group = 'Source'

    static catalog = [
        { key: 'wall-outlet',  label: 'Wall Outlet',  volts: 240, amps: 13  },
        { key: 'gen-30a',      label: 'Generator',    volts: 240, amps: 30  },
        { key: 'ship-reactor', label: 'Ship Reactor',  volts: 240, amps: 120 },
        { key: 'battery-12v',  label: 'Battery 12V',  volts: 12,  amps: 20  },
        { key: 'battery-48v',  label: 'Battery 48V',  volts: 48,  amps: 30  },
    ]

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            volts:     preset.volts ?? 240,
            amps:      preset.amps  ?? 13,
            live:      false,
            overload:  false,
            drawWatts: 0,
            drawAmps:  0,
            ripple:    preset.ripple ? { ...preset.ripple } : { enabled: false, amount: 2.0, interval: 0.8 },
            // Generators are sources only — no inbound pip
            pipsInbound:  [],
            pipsOutbound: [{ label: id, index: 0 }],
        }
    }

    static _defaultRipple() {
        return { enabled: false, amount: 2.0, interval: 0.8 }
    }

    static configFields() {
        return [...super.configFields(), 'volts', 'amps', 'live', 'ripple']
    }

    // Generators produce rather than receive — apply() is a no-op.
    static apply(panel, signal, graph) { /* source — does not process inbound */ }

    // ── Actions ───────────────────────────────────────────────────────────────

    /** Toggle generator on/off. A tripped generator resets on first click. */
    static toggle(panel, graph) {
        if (panel.state === 'tripped') {
            panel.overload = false
            panel.live     = false
            panel.state    = 'off'
            graph.emit(panel, null)
            graph.updateAllGenDraws()
            return
        }
        panel.live  = !panel.live
        panel.state = panel.live ? 'on' : 'off'
        graph.emit(panel, panel.live ? { v: panel.volts, a: panel.amps } : null)
        graph.updateAllGenDraws()
    }

    /** Call after volts or amps are changed on a live generator. */
    static paramsChanged(panel, graph) {
        if (panel.live && panel.state !== 'tripped') {
            panel.overload = false
            graph.emit(panel, { v: panel.volts, a: panel.amps })
            graph.updateAllGenDraws()
        }
    }

    static reset(panel, graph) {
        panel.live     = false
        panel.state    = 'off'
        panel.overload = false
        graph.emit(panel, null)
        graph.updateAllGenDraws()
    }
}

NodeRegistry.register(Generator)
