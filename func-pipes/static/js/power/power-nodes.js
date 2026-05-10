/*
  power-nodes.js
  ─────────────────────────────────────────────────────────────────────────────
  Per-node signal processors: breaker, bulb, load, meter.
*/

const NodeMethods = {

    _applyBreaker(panel, signal) {
        if (!signal || signal.v <= 0) {
            panel.state = 'off'
            this._emitPower(panel, null)
            return
        }
        if (panel.tripped) {
            panel.state = 'tripped'
            this._emitPower(panel, null)
            return
        }
        if (!panel.closed) {
            panel.state = 'open'
            this._emitPower(panel, null)
            return
        }
        // Auto-trip on over-current
        if (signal.a > panel.ratingAmps) {
            panel.tripped = true
            panel.state   = 'tripped'
            this._emitPower(panel, null)
            return
        }
        panel.state = 'closed'
        this._emitPower(panel, { v: signal.v, a: signal.a })
    },

    _applyBulb(panel, signal) {
        // Once blown, ignore all signals until manually reset.
        if (panel.blown) return

        if (!signal || signal.v <= 0 || signal.a <= 0) {
            panel.state = 'off'; panel.brightness = 0
            this._emitPower(panel, null)
            return
        }

        // Overcapacity check — voltage spike blows the bulb.
        if (signal.v > panel.maxVolts) {
            panel.blown      = true
            panel.state      = 'blown'
            panel.brightness = 0
            this._emitPower(panel, null)   // blown = open circuit
            return
        }

        const drawAmps   = panel.watts / NOMINAL_VOLTS
        const voltRatio  = signal.v  / NOMINAL_VOLTS
        const ampRatio   = signal.a  / drawAmps

        if (signal.v < 180 || signal.a < drawAmps * 0.05) {
            panel.state = 'off'; panel.brightness = 0
            this._emitPower(panel, null)
        } else if (voltRatio < 0.9 || ampRatio < 1) {
            panel.state      = 'dim'
            panel.brightness = Math.min(1, voltRatio * Math.min(1, ampRatio)) * 0.55
            this._emitPower(panel, null)
        } else {
            panel.state      = 'on'
            panel.brightness = Math.min(1.0, voltRatio)
            this._emitPower(panel, null)
        }
    },

    _applyLoad(panel, signal) {
        // Once blown, ignore all signals until manually reset.
        if (panel.blown) return

        const drawAmps = panel.watts / NOMINAL_VOLTS

        // Overcapacity: voltage exceeds rated maximum.
        if (signal && signal.v > panel.maxVolts) {
            panel.blown = true
            panel.state = 'blown'
            this._emitPower(panel, null)   // blown = open circuit
            return
        }

        const powered = signal && signal.v >= panel.minVolts && signal.a >= drawAmps

        if (powered) {
            panel._lastGoodSignal = signal
            panel.state = 'on'
            this._emitPower(panel, { v: signal.v, a: signal.a - drawAmps })
        } else if (!signal || signal.v <= 0) {
            // Fully dead — try capacitor
            if (panel.capacitance > 0 && panel.chargeWs > 0) {
                panel.state = 'capacitor'
                // Tick handles drain; emit a held signal based on last good
                const held = panel._lastGoodSignal
                if (held) this._emitPower(panel, { v: held.v, a: held.a - drawAmps })
            } else {
                panel.state = 'off'
                this._emitPower(panel, null)
            }
        } else {
            // Brownout: voltage or amps insufficient but not zero
            panel.state = 'brownout'
            this._emitPower(panel, null)
        }
    },

    _applyMeter(panel, signal) {
        if (!signal || signal.v <= 0) {
            panel.state = 'off'
            panel.volts = 0; panel.amps = 0; panel.watts = 0
            this._emitPower(panel, null)
            return
        }
        panel.state = 'on'
        panel.volts = +signal.v.toFixed(1)
        panel.amps  = +signal.a.toFixed(2)
        panel.watts = +(signal.v * signal.a).toFixed(0)
        this._emitPower(panel, signal)  // pass through unchanged
    },

    chargePercent(panel) {
        if (panel.capacitance <= 0) return 0
        return Math.min(100, (panel.chargeWs / panel.capacitance) * 100)
    },
}
