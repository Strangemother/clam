/*
  power-ripple.js
  ─────────────────────────────────────────────────────────────────────────────
  Power ripple — periodic voltage / current micro-fluctuations.

  Each ripple-capable node carries:
    ripple: {
      enabled:  bool    — master on/off for this node
      amount:   number  — maximum peak deviation in volts (±)
      interval: number  — seconds between ripple ticks
    }
    _rippleAccum:  number  — time accumulator (seconds, not persisted)
    _rippleOffset: number  — current voltage offset being injected (not persisted)

  Propagation model
  ─────────────────
  • Generator ripple: on each interval the gen re-emits { v: nominal + offset }.
    This noise travels downstream through every connected node automatically —
    breakers, bulbs, loads, meters all react to the changed signal as normal.

  • Load output ripple: active loads also jitter their *output* amps on each
    interval, representing switching transients (motor starts, PSU noise, etc.).
    The output amp offset is ±(amount / nominalVolts), proportional to wattage.

  • Converter attenuation: converters dampen the ripple amplitude of signals
    passing through them by a configurable factor (default 0.4 — meaning they
    pass 40% of the incoming ripple through, filtering 60%).

  Defaults by node type
  ─────────────────────
    gen       amount: 2V,    interval: 0.8s  (mains hum / generator governor)
    load      amount: 0.5V,  interval: 0.3s  (switching transient)
    converter amount: 1V,    interval: 1.2s  (output ripple / regulation lag)
*/

// ── default ripple profiles ────────────────────────────────────────────────
const RIPPLE_DEFAULTS = {
    gen:       { enabled: false, amount: 2.0,  interval: 0.8 },
    load:      { enabled: false, amount: 0.5,  interval: 0.3 },
    converter: { enabled: false, amount: 1.0,  interval: 1.2 },
}

// ── helper: bounded random offset ────────────────────────────────────────────
function _rippleRandom(amount) {
    return (Math.random() * 2 - 1) * amount   // uniform in [-amount, +amount]
}

// ── RippleMethods ─────────────────────────────────────────────────────────────

const RippleMethods = {

    /* Called from the rAF tick with dt (seconds since last frame). */
    _tickRipple(dt) {
        this.panels.forEach(p => {
            if (!p.ripple?.enabled) return

            p._rippleAccum = (p._rippleAccum || 0) + dt

            if (p._rippleAccum < p.ripple.interval) return
            p._rippleAccum = 0

            // Compute new random offset within ±amount
            p._rippleOffset = _rippleRandom(p.ripple.amount)

            if (p.type === 'gen' && p.live && p.state !== 'tripped') {
                // Re-emit with the offset baked into outgoing voltage.
                // Clamp to 1V minimum so we never emit negative/zero.
                const vOut = Math.max(1, p.volts + p._rippleOffset)
                this._emitPower(p, { v: vOut, a: p.amps })
            }

            if (p.type === 'load' && p.state === 'on' && p.signal) {
                // Loads inject output noise on their downstream pip.
                // The jitter is an amp variation proportional to rated watts.
                const drawAmps  = p.watts / NOMINAL_VOLTS
                const ampJitter = _rippleRandom(p.ripple.amount / NOMINAL_VOLTS)
                const aOut      = Math.max(0, p.signal.a - drawAmps + ampJitter)
                this._emitPower(p, { v: p.signal.v, a: aOut })
            }

            if (p.type === 'converter' && p.state !== 'off' && p.signal) {
                // Re-run converter logic with the current signal — the offset
                // will be factored by _applyConverterWithRipple via the signal itself.
                this._applyConverter(p, p.signal)
            }
        })
    },

    /* Toggle ripple for a node, initialising defaults the first time. */
    toggleRipple(panel) {
        if (!panel.ripple) this._initRipple(panel)
        panel.ripple.enabled = !panel.ripple.enabled
        if (!panel.ripple.enabled) {
            panel._rippleOffset = 0
            // Restore clean signal if this is a gen
            if (panel.type === 'gen' && panel.live) {
                this._emitPower(panel, { v: panel.volts, a: panel.amps })
                this._updateAllGenDraws()
            }
        }
    },

    /* Update ripple params and clamp to safe values. */
    rippleParamsChanged(panel) {
        if (!panel.ripple) return
        panel.ripple.amount   = Math.max(0.01, +panel.ripple.amount   || 0.1)
        panel.ripple.interval = Math.max(0.05, +panel.ripple.interval || 0.5)
    },

    /* Initialise ripple state on a panel that doesn't have it yet. */
    _initRipple(panel) {
        const def = RIPPLE_DEFAULTS[panel.type] || { enabled: false, amount: 1, interval: 1 }
        panel.ripple       = { ...def }
        panel._rippleAccum  = 0
        panel._rippleOffset = 0
    },
}
