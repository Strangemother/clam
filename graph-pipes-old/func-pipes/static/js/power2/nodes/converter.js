/*
  nodes/converter.js — Step-up / Step-down Transformer
  ─────────────────────────────────────────────────────────────────────────────
  Scales voltage up or down using a configurable target output voltage and
  efficiency factor, modelling an ideal transformer with I²R losses.

  Physics
  ───────
  turns ratio  = outVolts / _baseInVolts       (snapshotted on first live signal)
  P_in         = V_in × A_in
  P_out        = P_in × efficiency
  V_out        = V_in × turns_ratio            (tracks input — ripple passes through)
  A_out        = P_out / V_out

  _baseInVolts: the nominal input voltage captured on the first valid signal
  arrival. This locks the turns ratio so outVolts is met at that baseline.
  Changing outVolts or calling dialUp/Down re-locks to the current input.

  Extended state
  ──────────────
  outVolts     number  — target output voltage at nominal input
  step         number  — dial increment in volts
  efficiency   number  — power transfer factor (0–1; 1 = lossless)
  inVolts      number  — live measured input voltage
  inAmps       number  — live measured input current
  outAmps      number  — live computed output current
  ratio        number  — live V_out / V_in ratio
  _baseInVolts number  — snapshotted nominal input (defines turns ratio)

  States: 'off' | 'step-up' | 'step-down' | 'unity' | 'fault'
*/

class Converter extends NodeBase {

    static type  = 'converter'
    static label = 'Converter'
    static group = 'Converter'

    static catalog = [
        { key: 'conv-480v', label: 'Step-up  240→480V', outVolts: 480 },
        { key: 'conv-24v',  label: 'Step-down 240→24V', outVolts: 24  },
        { key: 'conv-12v',  label: 'Step-down 240→12V', outVolts: 12  },
        { key: 'conv-5v',   label: 'Step-down 240→5V',  outVolts: 5   },
        { key: 'psu-atx',   label: 'ATX PSU (12V)',      outVolts: 12,  efficiency: 0.88 },
    ]

    static _defaultRipple() {
        return { enabled: false, amount: 1.0, interval: 1.2 }
    }

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            outVolts:     preset.outVolts   ?? 120,
            step:         preset.step       ?? 10,
            efficiency:   preset.efficiency ?? 0.95,
            inVolts:      0,
            inAmps:       0,
            outAmps:      0,
            ratio:        null,
            _baseInVolts: null,
            ripple:       preset.ripple ? { ...preset.ripple } : { ...this._defaultRipple() },
        }
    }

    static configFields() {
        return [...super.configFields(), 'outVolts', 'step', 'efficiency', 'ripple']
    }

    /**
     * Transform the inbound signal. On the first live signal the turns ratio is
     * locked (snapshotting the base input voltage). Subsequent frames track any
     * ripple that passes through. Emits the converted { v, a } downstream and
     * throttles 'converter:reading' events when values change.
     * @param {Object}     panel
     * @param {Object|null} signal — upstream { v, a } or null
     * @param {PowerGraph} graph
     */
    static apply(panel, signal, graph) {
        if (!signal || signal.v <= 0 || signal.a <= 0) {
            const prev    = panel.state
            panel.state   = 'off'
            panel.inVolts = 0
            panel.inAmps  = 0
            panel.outAmps = 0
            panel.ratio   = null
            if (prev !== 'off') Converter.dispatch(panel, 'state:change', { from: prev, to: 'off' })
            graph.emit(panel, null)
            return
        }

        // Snapshot the base input voltage on first live signal.
        if (!panel._baseInVolts) panel._baseInVolts = signal.v

        const turnsRatio = panel.outVolts / panel._baseInVolts
        const pIn  = signal.v * signal.a
        const pOut = pIn * panel.efficiency
        const vOut = signal.v * turnsRatio      // tracks input; ripple passes through
        const aOut = vOut > 0 ? pOut / vOut : 0

        panel.inVolts = +signal.v.toFixed(1)
        panel.inAmps  = +signal.a.toFixed(2)
        panel.outAmps = +aOut.toFixed(2)
        panel.ratio   = +(vOut / signal.v).toFixed(3)

        if (vOut <= 0 || aOut <= 0) {
            const prev  = panel.state
            panel.state = 'fault'
            if (prev !== 'fault') Converter.dispatch(panel, 'converter:fault', { inVolts: panel.inVolts, inAmps: panel.inAmps })
            if (prev !== 'fault') Converter.dispatch(panel, 'state:change', { from: prev, to: 'fault' })
            graph.emit(panel, null)
            return
        }

        const prev  = panel.state
        panel.state = panel.ratio > 1.005
            ? 'step-up'
            : panel.ratio < 0.995
                ? 'step-down'
                : 'unity'

        if (panel.state !== prev)
            Converter.dispatch(panel, 'state:change', { from: prev, to: panel.state })

        const vOutR = +vOut.toFixed(1)
        if (vOutR !== panel._lastOutVolts || panel.outAmps !== panel._lastOutAmps) {
            panel._lastOutVolts = vOutR
            panel._lastOutAmps  = panel.outAmps
            Converter.throttle(panel, 'converter:reading', { inVolts: panel.inVolts, inAmps: panel.inAmps, outVolts: vOutR, outAmps: panel.outAmps, ratio: panel.ratio })
        }

        graph.emit(panel, { v: vOutR, a: aOut })
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    static dialUp(panel, graph) {
        panel.outVolts     = +(panel.outVolts + panel.step).toFixed(1)
        panel._baseInVolts = panel.signal?.v || null
        Converter.dispatch(panel, 'converter:dial', { outVolts: panel.outVolts, direction: 'up' })
        this.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    static dialDown(panel, graph) {
        panel.outVolts     = Math.max(1, +(panel.outVolts - panel.step).toFixed(1))
        panel._baseInVolts = panel.signal?.v || null
        Converter.dispatch(panel, 'converter:dial', { outVolts: panel.outVolts, direction: 'down' })
        this.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    /**
     * Clamp and validate outVolts / step / efficiency after external edits (e.g.
     * config panel), re-lock the turns ratio, and re-emit downstream.
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static paramsChanged(panel, graph) {
        panel.outVolts   = Math.max(1,    +panel.outVolts   || 1)
        panel.step       = Math.max(0.1,  +panel.step       || 10)
        panel.efficiency = Math.min(1, Math.max(0.01, +panel.efficiency || 0.95))
        panel._baseInVolts = panel.signal?.v || null
        Converter.dispatch(panel, 'converter:params', { outVolts: panel.outVolts, efficiency: panel.efficiency })
        this.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    /**
     * Clear all measured values and the locked turns-ratio snapshot, then
     * delegate to NodeBase.reset().
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static reset(panel, graph) {
        panel.inVolts      = 0
        panel.inAmps       = 0
        panel.outAmps      = 0
        panel.ratio        = null
        panel._baseInVolts = null
        panel._lastOutVolts = null
        panel._lastOutAmps  = null
        panel.powerSources = {}
        Converter.dispatch(panel, 'converter:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Converter)
