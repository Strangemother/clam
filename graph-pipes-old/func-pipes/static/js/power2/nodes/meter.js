/*
  nodes/meter.js — Instrument / Power Meter
  ─────────────────────────────────────────────────────────────────────────────
  A read-only instrument: measures and displays V / A / W, then passes
  the signal through to downstream nodes unchanged.

  Extended state
  ──────────────
  volts  number  — measured voltage
  amps   number  — measured current
  watts  number  — computed power (V × A)

  States: 'off' | 'on'
*/

class Meter extends NodeBase {

    static type  = 'meter'
    static label = 'Meter'
    static group = 'Instrument'

    static catalog = [
        { key: 'meter', label: 'Power Meter' },
    ]

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            volts: 0,
            amps:  0,
            watts: 0,
        }
    }

    static configFields() {
        return [...super.configFields()]   // no extra config beyond label
    }

    /**
     * Measure the inbound signal and pass it through unchanged. Readings are
     * throttled and emitted as 'meter:reading' events when V or A changes.
     * @param {Object}     panel
     * @param {Object|null} signal — upstream { v, a } or null
     * @param {PowerGraph} graph
     */
    static apply(panel, signal, graph) {
        if (!signal || signal.v <= 0) {
            const prev  = panel.state
            panel.state = 'off'
            panel.volts = 0
            panel.amps  = 0
            panel.watts = 0
            if (prev !== 'off') Meter.dispatch(panel, 'state:change', { from: prev, to: 'off' })
            graph.emit(panel, null)
            return
        }

        const prev  = panel.state
        const volts = +signal.v.toFixed(1)
        const amps  = +signal.a.toFixed(2)
        const watts = +(signal.v * signal.a).toFixed(0)

        panel.state = 'on'
        panel.volts = volts
        panel.amps  = amps
        panel.watts = watts

        if (prev !== 'on') Meter.dispatch(panel, 'state:change', { from: prev, to: 'on' })

        if (volts !== panel._lastVolts || amps !== panel._lastAmps) {
            panel._lastVolts = volts
            panel._lastAmps  = amps
            Meter.throttle(panel, 'meter:reading', { volts, amps, watts })
        }

        graph.emit(panel, signal)   // transparent pass-through
    }

    /**
     * Reset all readings to zero, clear internal de-dupe tracking, and
     * propagate to NodeBase.reset().
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static reset(panel, graph) {
        panel.volts        = 0
        panel.amps         = 0
        panel.watts        = 0
        panel._lastVolts   = null
        panel._lastAmps    = null
        panel.powerSources = {}
        Meter.dispatch(panel, 'meter:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Meter)
