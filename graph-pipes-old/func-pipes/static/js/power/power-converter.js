/*
  power-converter.js
  ─────────────────────────────────────────────────────────────────────────────
  Step-up / step-down transformer node.

  Physics (ideal transformer + efficiency loss):
    turns ratio = outVolts / _baseInVolts
    P_in  = V_in × A_in
    P_out = P_in × efficiency
    V_out = V_in × turns_ratio   ← tracks live input, including ripple
    A_out = P_out / V_out

  _baseInVolts is the nominal input voltage snapshotted the first time a
  stable signal arrives, or reset when the user changes outVolts / dials.
  outVolts is therefore a *target* at nominal input, not a hard clamp.

  Dial controls:
    converterDialUp(panel)   — increase outVolts target by panel.step
    converterDialDown(panel) — decrease outVolts target by panel.step (min 1V)
*/

const ConverterMethods = {

    _applyConverter(panel, signal) {
        if (!signal || signal.v <= 0 || signal.a <= 0) {
            panel.state   = 'off'
            panel.inVolts = 0
            panel.inAmps  = 0
            panel.outAmps = 0
            panel.ratio   = null
            this._emitPower(panel, null)
            return
        }

        // Snapshot the base input the first time we see a live signal.
        // This locks the turns ratio so the target outVolts is met at this voltage.
        if (!panel._baseInVolts) panel._baseInVolts = signal.v

        const turnsRatio = panel.outVolts / panel._baseInVolts
        const pIn  = signal.v * signal.a
        const pOut = pIn * panel.efficiency
        const vOut = signal.v * turnsRatio          // tracks input — ripple passes through
        const aOut = vOut > 0 ? pOut / vOut : 0

        panel.inVolts = +signal.v.toFixed(1)
        panel.inAmps  = +signal.a.toFixed(2)
        panel.outAmps = +aOut.toFixed(2)
        panel.ratio   = +(vOut / signal.v).toFixed(3)

        if (vOut <= 0 || aOut <= 0) {
            panel.state = 'fault'
            this._emitPower(panel, null)
            return
        }

        panel.state = panel.ratio > 1.005
            ? 'step-up'
            : panel.ratio < 0.995
                ? 'step-down'
                : 'unity'

        this._emitPower(panel, { v: +vOut.toFixed(1), a: aOut })
    },

    converterDialUp(panel) {
        panel.outVolts    = +(panel.outVolts + panel.step).toFixed(1)
        panel._baseInVolts = panel.signal?.v || null   // re-lock ratio to current input
        this._applyConverter(panel, panel.signal)
        this._updateAllGenDraws()
    },

    converterDialDown(panel) {
        panel.outVolts    = Math.max(1, +(panel.outVolts - panel.step).toFixed(1))
        panel._baseInVolts = panel.signal?.v || null   // re-lock ratio to current input
        this._applyConverter(panel, panel.signal)
        this._updateAllGenDraws()
    },

    converterParamsChanged(panel) {
        panel.outVolts   = Math.max(1,    +panel.outVolts   || 1)
        panel.step       = Math.max(0.1,  +panel.step       || 10)
        panel.efficiency = Math.min(1, Math.max(0.01, +panel.efficiency || 0.95))
        panel._baseInVolts = panel.signal?.v || null   // re-lock ratio to current input
        this._applyConverter(panel, panel.signal)
        this._updateAllGenDraws()
    },
}
