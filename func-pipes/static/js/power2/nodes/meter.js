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

    static apply(panel, signal, graph) {
        if (!signal || signal.v <= 0) {
            panel.state = 'off'
            panel.volts = 0
            panel.amps  = 0
            panel.watts = 0
            graph.emit(panel, null)
            return
        }

        panel.state = 'on'
        panel.volts = +signal.v.toFixed(1)
        panel.amps  = +signal.a.toFixed(2)
        panel.watts = +(signal.v * signal.a).toFixed(0)
        graph.emit(panel, signal)   // transparent pass-through
    }

    static reset(panel, graph) {
        panel.volts        = 0
        panel.amps         = 0
        panel.watts        = 0
        panel.powerSources = {}
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Meter)
