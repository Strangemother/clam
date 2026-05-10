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
  minVolts        number  — below this the load will not operate (brownout)
  maxVolts        number  — above this the load blows (overvoltage)
  capacitance     number  — watt-second buffer (0 = no capacitor)
  chargeWs        number  — current stored charge in watt-seconds
  blown           bool    — destroyed by overvoltage; requires manual reset
  _lastGoodSignal Object  — last { v, a } when fully powered (for cap rundown)

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
        { key: 'fan',       label: 'Fan',         watts: 25,   minVolts: 200 },
        { key: 'pump',      label: 'Pump',         watts: 180,  minVolts: 210 },
        { key: 'motor-sm',  label: 'Motor (sm)',   watts: 370,  minVolts: 215 },
        { key: 'motor-lg',  label: 'Motor (lg)',   watts: 1500, minVolts: 220 },
        { key: 'ups',       label: 'UPS Buffer',   watts: 5,    minVolts: 190, capacitance: 600 },
    ]

    static _defaultRipple() {
        return { enabled: false, amount: 0.5, interval: 0.3 }
    }

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            watts:           preset.watts       ?? 100,
            minVolts:        preset.minVolts    ?? 200,
            maxVolts:        preset.maxVolts    ?? (preset.minVolts ? preset.minVolts * 1.25 : 300),
            capacitance:     preset.capacitance ?? 0,
            chargeWs:        0,
            blown:           false,
            _lastGoodSignal: null,
            ripple:          preset.ripple ? { ...preset.ripple } : { ...this._defaultRipple() },
        }
    }

    static configFields() {
        return [...super.configFields(), 'watts', 'minVolts', 'maxVolts', 'capacitance', 'ripple']
    }

    static apply(panel, signal, graph) {
        if (panel.blown) return   // open circuit until manually reset

        const drawAmps = panel.watts / NOMINAL_VOLTS
        const prev     = panel.state

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

    static tick(panel, dt, graph) {
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

    static paramsChanged(panel, graph) {
        if (panel.signal !== undefined) {
            // Dispatch through registry so subclasses (Heater, Console…) use their own apply.
            const Cls = NodeRegistry.get(panel.type)
            if (Cls) Cls.apply(panel, panel.signal, graph)
        }
        graph.updateAllGenDraws()
    }

    static chargePercent(panel) {
        if (panel.capacitance <= 0) return 0
        return Math.min(100, (panel.chargeWs / panel.capacitance) * 100)
    }

    static reset(panel, graph) {
        panel.blown          = false
        panel.chargeWs       = 0
        panel._lastGoodSignal = null
        panel.powerSources   = {}
        Load.dispatch(panel, 'load:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Load)
