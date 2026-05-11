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
    static dispatchDelay = 200  // draw telemetry throttle rate

    static _defaultSpike() {
        return { enabled: true, percent: 15, duration: 0.94 }
    }

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
        return [...super.configFields(), 'volts', 'amps', 'live', 'ripple', 'spike']
    }

    // Generators produce rather than receive — apply() is a no-op.
    static apply(panel, signal, graph) { /* source — does not process inbound */ }

    // Decay the inrush spike each frame and re-emit the settled or spiked output signal.
    static tick(panel, dt, graph) {
        const wasNonZero = (panel._spikeTimer ?? 0) > 0
        const active     = NodeBase.tickSpike(panel, dt)
        if (!active && !wasNonZero) return
        if (!panel.live || panel.state === 'tripped' || panel.state === 'off') return
        const m = NodeBase.spikeMultiplier(panel)
        graph.emit(panel, { v: +(panel.volts * m).toFixed(2), a: +(panel.amps * m).toFixed(3) })
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    /** Toggle generator on/off. A tripped generator resets on first click. */
    static toggle(panel, graph) {
        if (panel.state === 'tripped') {
            panel.overload = false
            panel.live     = false
            panel.state    = 'off'
            Generator.dispatch(panel, 'state:change', { from: 'tripped', to: 'off' })
            graph.emit(panel, null)
            graph.updateAllGenDraws()
            return
        }
        const prev  = panel.state
        panel.live  = !panel.live
        panel.state = panel.live ? 'on' : 'off'
        Generator.dispatch(panel, 'state:change', { from: prev, to: panel.state })
        Generator.dispatch(panel, panel.live ? 'gen:start' : 'gen:stop', { volts: panel.volts, amps: panel.amps })
        if (panel.live) {
            NodeBase.startSpike(panel)
            const m = NodeBase.spikeMultiplier(panel)
            graph.emit(panel, { v: +(panel.volts * m).toFixed(2), a: +(panel.amps * m).toFixed(3) })
        } else {
            graph.emit(panel, null)
        }
        graph.updateAllGenDraws()
    }

    /** Call after volts or amps are changed on a live generator. */
    static paramsChanged(panel, graph) {
        if (panel.live && panel.state !== 'tripped') {
            panel.overload = false
            Generator.dispatch(panel, 'gen:params', { volts: panel.volts, amps: panel.amps })
            graph.emit(panel, { v: panel.volts, a: panel.amps })
            graph.updateAllGenDraws()
        }
    }

    static reset(panel, graph) {
        const prev     = panel.state
        panel.live     = false
        panel.state    = 'off'
        panel.overload = false
        Generator.dispatch(panel, 'gen:reset', { from: prev })
        graph.emit(panel, null)
        graph.updateAllGenDraws()
    }

    /**
     * Hook called by graph.computeGenDraw() after BFS + state updates complete.
     * Emits events only — state is already set by the graph.
     */
    static onDrawUpdated(panel, graph) {
        // State-change events — dispatch immediately on transitions
        const state = panel.state
        if (state !== panel._lastEmittedState) {
            if (state === 'tripped')
                Generator.dispatch(panel, 'gen:tripped', { drawAmps: +panel.drawAmps.toFixed(2), ratedAmps: panel.amps })
            else if (state === 'sag')
                Generator.dispatch(panel, 'gen:sag', { drawAmps: +panel.drawAmps.toFixed(2), ratedAmps: panel.amps })
            Generator.dispatch(panel, 'state:change', { from: panel._lastEmittedState ?? 'off', to: state })
            panel._lastEmittedState = state
        }

        // Draw telemetry — only when draw has changed, then throttled at dispatchDelay (200ms)
        if (panel.live) {
            const ratio    = panel.amps > 0 ? panel.drawAmps / panel.amps : 0
            const drawW    = +panel.drawWatts.toFixed(1)
            const drawA    = +panel.drawAmps.toFixed(2)
            if (drawW !== panel._lastDrawWatts || drawA !== panel._lastDrawAmps) {
                panel._lastDrawWatts = drawW
                panel._lastDrawAmps  = drawA
                Generator.throttle(panel, 'gen:draw', {
                    drawWatts: drawW,
                    drawAmps:  drawA,
                    ratedAmps: panel.amps,
                    load:      +ratio.toFixed(2),
                })
            }
        }
    }
}

NodeRegistry.register(Generator)
