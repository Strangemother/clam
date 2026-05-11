/*
  nodes/bulb.js — Resistive Lamp (sink)
  ─────────────────────────────────────────────────────────────────────────────
  A visual power sink. Brightness grades between off, dim, and fully lit.
  No outbound pip — it consumes all power reaching it.

  Extended state
  ──────────────
  watts       number  — rated wattage (determines amp draw)
  maxVolts    number  — above this the bulb blows (overvoltage)
  maxAmps     number  — above this the bulb blows (overcurrent)
  brightness  number  — 0.0–1.0 (used for CSS / animation)
  blown       bool    — destroyed by overvoltage or overcurrent; requires manual reset

  States: 'off' | 'dim' | 'on' | 'blown'
*/

class Bulb extends NodeBase {

    static type  = 'bulb'
    static label = 'Bulb'
    static group = 'Light'

    static _defaultSpike() {
        return { enabled: true, percent: 25, duration: 0.73 }
    }

    static catalog = [
        { key: 'led-5w',    label: 'LED  5W',    watts: 5   },
        { key: 'bulb-40w',  label: 'Bulb  40W',  watts: 40  },
        { key: 'bulb-60w',  label: 'Bulb  60W',  watts: 60  },
        { key: 'bulb-100w', label: 'Bulb 100W',  watts: 100 },
    ]

    static defaults(id, preset = {}) {
        const watts = preset.watts ?? 60
        return {
            ...super.defaults(id, preset),
            watts,
            maxVolts:   preset.maxVolts ?? (preset.volts ? preset.volts * 1.2 : 288),
            maxAmps:    preset.maxAmps  ?? +((watts / NOMINAL_VOLTS) * 2).toFixed(3),
            brightness: 0,
            blown:      false,
            spike:      preset.spike ? { ...preset.spike } : { ...this._defaultSpike() },
            _spikeWatts: 0,
            // Bulbs are sinks — no outbound pip
            pipsOutbound: [],
        }
    }

    static configFields() {
        return [...super.configFields(), 'watts', 'maxVolts', 'maxAmps', 'spike']
    }

    static apply(panel, signal, graph) {
        if (panel.blown) return   // blown = open circuit until manually reset

        if (!signal || signal.v <= 0 || signal.a <= 0) {
            const prev = panel.state
            panel.state      = 'off'
            panel.brightness = 0
            if (prev !== 'off') Bulb.dispatch(panel, 'state:change', { from: prev, to: 'off' })
            graph.emit(panel, null)
            return
        }

        if (signal.v > panel.maxVolts) {
            const prev = panel.state
            panel.blown      = true
            panel.state      = 'blown'
            panel.brightness = 0
            Bulb.dispatch(panel, 'bulb:blown', { reason: 'overvoltage', volts: signal.v, maxVolts: panel.maxVolts })
            Bulb.dispatch(panel, 'state:change', { from: prev, to: 'blown' })
            graph.emit(panel, null)
            return
        }

        if (signal.a > panel.maxAmps) {
            const prev = panel.state
            panel.blown      = true
            panel.state      = 'blown'
            panel.brightness = 0
            Bulb.dispatch(panel, 'bulb:blown', { reason: 'overcurrent', amps: signal.a, maxAmps: panel.maxAmps })
            Bulb.dispatch(panel, 'state:change', { from: prev, to: 'blown' })
            graph.emit(panel, null)
            return
        }

        const drawAmps  = panel.watts / NOMINAL_VOLTS
        const voltRatio = signal.v / NOMINAL_VOLTS
        const ampRatio  = signal.a / drawAmps

        const prev      = panel.state
        const prevBrightness = panel.brightness

        if (signal.v < 180 || signal.a < drawAmps * 0.05) {
            panel.state      = 'off'
            panel.brightness = 0
        } else if (voltRatio < 0.9 || ampRatio < 1) {
            panel.state      = 'dim'
            panel.brightness = Math.min(1, voltRatio * Math.min(1, ampRatio)) * 0.55
            if (prev !== 'dim') Bulb.dispatch(panel, 'bulb:brownout', { volts: signal.v, amps: signal.a })
        } else {
            panel.state      = 'on'
            panel.brightness = Math.min(1.0, voltRatio)
            if (prev !== 'on') NodeBase.startSpike(panel)
        }

        if (panel.state !== prev)
            Bulb.dispatch(panel, 'state:change', { from: prev, to: panel.state })
        if (Math.abs(panel.brightness - prevBrightness) >= 0.05)
            Bulb.dispatch(panel, 'bulb:brightness', { brightness: +panel.brightness.toFixed(2) })

        graph.emit(panel, null)   // sink — nothing forwarded
    }

    static tick(panel, dt, graph) {
        const wasSpiking = NodeBase.tickSpike(panel, dt)
        // Track inflated watt draw so computeGenDraw picks it up during the spike.
        panel._spikeWatts = (panel.state === 'on' || panel.state === 'dim')
            ? panel.watts * NodeBase.spikeMultiplier(panel)
            : 0
        if (wasSpiking && panel.state !== 'off' && panel.state !== 'blown' && panel.signal)
            Bulb.apply(panel, panel.signal, graph)
    }

    static reset(panel, graph) {
        panel.blown      = false
        panel.brightness = 0
        panel.powerSources = {}
        Bulb.dispatch(panel, 'bulb:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Bulb)
