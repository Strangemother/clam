/*
  nodes/load.js — Generic Configurable Load
  ─────────────────────────────────────────────────────────────────────────────
  A general-purpose power consumer. Passes remaining amps downstream,
  supports brownout detection, and optionally buffers power via a capacitor.

  This class is also the base for specialised load types (Heater, ConsoleNode).
  Extend it and override defaults() / tick() / apply() as needed.

  Extended state
  ──────────────
  watts           number  — rated wattage
  currentWatts    number  — live effective draw (modulated by noise + spike)
  minVolts        number  — below this the load will not operate (brownout)
  maxVolts        number  — above this the load blows (overvoltage)
  capacitance     number  — watt-second buffer (0 = no capacitor)
  chargeWs        number  — current stored charge in watt-seconds
  blown           bool    — destroyed by overvoltage; requires manual reset
  _lastGoodSignal Object  — last { v, a } when fully powered (for cap rundown)
  noise           Object  — { enabled, period, amount } periodic draw oscillation

  States: 'off' | 'on' | 'brownout' | 'capacitor' | 'blown'
*/

class Load extends NodeBase {

    static type  = 'load'
    static label = 'Load'
    static group = 'Load'

    /**
     * Marks this node class (and all subclasses) as watt-consuming.
     * Graph.computeGenDraw() uses this flag so custom Load subclasses
     * are automatically counted without modifying the engine.
     */
    static consumesWatts = true

    static catalog = [
        { key: 'fan',       label: 'Fan',         watts: 25,   minVolts: 200,
          spike:  { enabled: true,  percent: 40, duration: 0.6 },
          ripple: { enabled: true,  amount: 1.2, interval: 0.08 },
          noise:  { enabled: true,  period: 0.5, amount: 0.20 } },
        { key: 'pump',      label: 'Pump',         watts: 180,  minVolts: 210,
          spike:  { enabled: true,  percent: 45, duration: 0.8 },
          ripple: { enabled: true,  amount: 2.0, interval: 0.12 },
          noise:  { enabled: true,  period: 1.0, amount: 0.15 } },
        { key: 'motor-sm',  label: 'Motor (sm)',   watts: 370,  minVolts: 215,
          spike:  { enabled: true,  percent: 50, duration: 0.9 },
          ripple: { enabled: true,  amount: 2.5, interval: 0.15 },
          noise:  { enabled: true,  period: 1.5, amount: 0.12 } },
        { key: 'motor-lg',  label: 'Motor (lg)',   watts: 1500, minVolts: 220,
          spike:  { enabled: true,  percent: 60, duration: 1.2 },
          ripple: { enabled: true,  amount: 4.0, interval: 0.18 },
          noise:  { enabled: true,  period: 2.5, amount: 0.08 } },
        { key: 'ups',       label: 'UPS Buffer',   watts: 5,    minVolts: 190, capacitance: 600,
          spike:  { enabled: true,  percent: 5,  duration: 0.2 },
          ripple: { enabled: false, amount: 0.1, interval: 1.0 },
          noise:  { enabled: false, period: 5.0, amount: 0.02 } },
    ]

    static _defaultRipple() {
        return { enabled: false, amount: 0.5, interval: 0.3 }
    }

    static _defaultSpike() {
        return { enabled: true, percent: 20, duration: 0.95 }
    }

    static _defaultNoise() {
        return { enabled: false, period: 2.0, amount: 0.1 }
    }

    static defaults(id, preset = {}) {
        const watts = preset.watts ?? 100
        return {
            ...super.defaults(id, preset),
            watts,
            currentWatts:    watts,
            minVolts:        preset.minVolts    ?? 200,
            maxVolts:        preset.maxVolts    ?? (preset.minVolts ? preset.minVolts * 1.25 : 300),
            capacitance:     preset.capacitance ?? 0,
            chargeWs:        0,
            blown:           false,
            _lastGoodSignal: null,
            _noiseAccum:     0,
            _noisePhase:     Math.random() * Math.PI * 2,
            _lastNoiseWatts: null,
            ripple:          preset.ripple ? { ...preset.ripple } : { ...this._defaultRipple() },
            spike:           preset.spike  ? { ...preset.spike  } : { ...this._defaultSpike()  },
            noise:           preset.noise  ? { ...preset.noise  } : { ...this._defaultNoise()  },
        }
    }

    static configFields() {
        return [...super.configFields(), 'watts', 'minVolts', 'maxVolts', 'capacitance', 'ripple', 'spike', 'noise']
    }

    static apply(panel, signal, graph) {
        if (panel.blown) return   // open circuit until manually reset

        const prev     = panel.state
        // currentWatts holds the live effective draw (noise-modulated, or rated for plain loads)
        const drawAmps = ((panel.currentWatts ?? panel.watts) / NOMINAL_VOLTS) * NodeBase.spikeMultiplier(panel)

        if (signal && signal.v > panel.maxVolts) {
            panel.blown = true
            panel.state = 'blown'
            Load.dispatch(panel, 'load:blown', { volts: signal.v, maxVolts: panel.maxVolts })
            Load.dispatch(panel, 'state:change', { from: prev, to: 'blown' })
            graph.emit(panel, null)
            return
        }

        const powered = signal && signal.v >= panel.minVolts && signal.a >= drawAmps

        if (powered) {
            if (prev !== 'on' && prev !== 'capacitor') NodeBase.startSpike(panel)
            panel._lastGoodSignal = signal
            panel.state = 'on'
            graph.emit(panel, { v: signal.v, a: signal.a - drawAmps })
        } else if (!signal || signal.v <= 0) {
            if (panel.capacitance > 0 && panel.chargeWs > 0) {
                panel.state = 'capacitor'
                const held = panel._lastGoodSignal
                if (held) graph.emit(panel, { v: held.v, a: held.a - drawAmps })
                if (prev !== 'capacitor')
                    Load.dispatch(panel, 'load:capacitor-failover', { chargeWs: panel.chargeWs })
            } else {
                panel.state = 'off'
                graph.emit(panel, null)
            }
        } else {
            panel.state = 'brownout'
            if (prev !== 'brownout')
                Load.dispatch(panel, 'load:brownout', { volts: signal.v, amps: signal.a, minVolts: panel.minVolts })
            graph.emit(panel, null)
        }

        if (panel.state !== prev)
            Load.dispatch(panel, 'state:change', { from: prev, to: panel.state })
    }

    /**
     * Per-frame update. Handles three independent concerns:
     *   1. Noise — applies a sine-wave draw oscillation when enabled.
     *   2. Spike decay — re-applies signal while the inrush spike is active.
     *   3. Capacitor — charges the buffer when on; drains it when off.
     * @param {Object}     panel
     * @param {number}     dt    — elapsed seconds since last tick
     * @param {PowerGraph} graph
     */
    static tick(panel, dt, graph) {
        // ── Noise: periodic sine-wave draw oscillation ───────────────────────
        if (panel.noise?.enabled && (panel.state === 'on' || panel.state === 'capacitor')) {
            panel._noiseAccum += dt
            const period = Math.max(0.1, panel.noise.period ?? 2.0)
            const amount = panel.noise.amount ?? 0.1
            const sine   = Math.sin(2 * Math.PI * (panel._noiseAccum / period) + (panel._noisePhase ?? 0))
            panel.currentWatts = panel.watts * (1 + amount * sine)

            const prev = panel._lastNoiseWatts ?? -1
            if (Math.abs(panel.currentWatts - prev) > 1) {
                panel._lastNoiseWatts = panel.currentWatts
                const Cls = NodeRegistry.get(panel.type)
                if (Cls && panel.signal) Cls.apply(panel, panel.signal, graph)
            }
        }

        // ── Spike decay: re-apply on each spiking frame, and on settle ───────
        const wasNonZero  = (panel._spikeTimer ?? 0) > 0
        const stillActive = NodeBase.tickSpike(panel, dt)
        if (stillActive || (wasNonZero && !stillActive)) {
            if ((panel.state === 'on' || panel.state === 'capacitor') && panel.signal) {
                const Cls = NodeRegistry.get(panel.type)
                if (Cls) Cls.apply(panel, panel.signal, graph)
            }
        }

        if (panel.capacitance <= 0) return

        if (panel.state === 'on') {
            panel.chargeWs = Math.min(panel.capacitance, panel.chargeWs + panel.watts * dt)
        } else if (panel.state === 'capacitor') {
            panel.chargeWs -= panel.watts * dt
            if (panel.chargeWs <= 0) {
                panel.chargeWs = 0
                panel.state    = 'off'
                Load.dispatch(panel, 'state:change', { from: 'capacitor', to: 'off' })
                graph.emit(panel, null)
            }
        }
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    /**
     * Re-evaluate signal processing after external parameter changes. Routes
     * through the NodeRegistry so subclasses (Heater, ConsoleNode, etc.) use
     * their own `apply()` rather than Load's.
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static paramsChanged(panel, graph) {
        if (panel.signal !== undefined) {
            // Dispatch through registry so subclasses (Heater, Console…) use their own apply.
            const Cls = NodeRegistry.get(panel.type)
            if (Cls) Cls.apply(panel, panel.signal, graph)
        }
        graph.updateAllGenDraws()
    }

    /**
     * Returns the current capacitor charge as a 0–100 percentage.
     * Returns 0 if no capacitor is fitted (capacitance = 0).
     * @param  {Object} panel
     * @returns {number}
     */
    static chargePercent(panel) {
        if (panel.capacitance <= 0) return 0
        return Math.min(100, (panel.chargeWs / panel.capacitance) * 100)
    }

    static reset(panel, graph) {
        panel.blown           = false
        panel.chargeWs        = 0
        panel.currentWatts    = panel.watts
        panel._noiseAccum     = 0
        panel._lastNoiseWatts = null
        panel._lastGoodSignal = null
        panel.powerSources    = {}
        Load.dispatch(panel, 'load:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Load)
