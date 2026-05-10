/*
  nodes/breaker.js — Circuit Breaker / Relay
  ─────────────────────────────────────────────────────────────────────────────
  Manual open/close switch with automatic over-current trip protection.

  Extended state
  ──────────────
  closed      bool    — manual closed/open toggle
  tripped     bool    — auto-tripped on over-current; reset by opening
  ratingAmps  number  — trip threshold

  States: 'off' | 'closed' | 'open' | 'tripped'
*/

class Breaker extends NodeBase {

    static type  = 'breaker'
    static label = 'Breaker'
    static group = 'Control'

    static catalog = [
        { key: 'breaker-6a',  label: 'Breaker  6A',  ratingAmps: 6  },
        { key: 'breaker-13a', label: 'Breaker 13A',  ratingAmps: 13 },
        { key: 'breaker-30a', label: 'Breaker 30A',  ratingAmps: 30 },
        { key: 'relay',       label: 'Relay',         ratingAmps: 10 },
    ]

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            ratingAmps: preset.ratingAmps ?? 16,
            closed:     true,
            tripped:    false,
        }
    }

    static configFields() {
        return [...super.configFields(), 'ratingAmps']
    }

    static apply(panel, signal, graph) {
        const prev = panel.state
        if (!signal || signal.v <= 0) {
            panel.state = 'off'
            if (prev !== 'off') Breaker.dispatch(panel, 'state:change', { from: prev, to: 'off' })
            graph.emit(panel, null)
            return
        }
        if (panel.tripped) {
            panel.state = 'tripped'
            if (prev !== 'tripped') {
                Breaker.dispatch(panel, 'breaker:tripped', { amps: signal.a, ratingAmps: panel.ratingAmps })
                Breaker.dispatch(panel, 'state:change', { from: prev, to: 'tripped' })
            }
            graph.emit(panel, null)
            return
        }
        if (!panel.closed) {
            panel.state = 'open'
            if (prev !== 'open') Breaker.dispatch(panel, 'state:change', { from: prev, to: 'open' })
            graph.emit(panel, null)
            return
        }
        if (signal.a > panel.ratingAmps) {
            panel.tripped = true
            panel.state   = 'tripped'
            Breaker.dispatch(panel, 'breaker:tripped', { amps: signal.a, ratingAmps: panel.ratingAmps })
            Breaker.dispatch(panel, 'state:change', { from: prev, to: 'tripped' })
            graph.emit(panel, null)
            return
        }
        panel.state = 'closed'
        if (prev !== 'closed') Breaker.dispatch(panel, 'state:change', { from: prev, to: 'closed' })
        graph.emit(panel, { v: signal.v, a: signal.a })
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    /** Toggle open/close (also resets a tripped breaker to open). */
    static toggle(panel, graph) {
        if (panel.tripped) {
            panel.tripped = false
            panel.closed  = false
        } else {
            panel.closed = !panel.closed
        }
        Breaker.dispatch(panel, 'breaker:toggle', { closed: panel.closed, tripped: panel.tripped })
        this.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    static reset(panel, graph) {
        panel.tripped      = false
        panel.closed       = true
        panel.powerSources = {}
        Breaker.dispatch(panel, 'breaker:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Breaker)
