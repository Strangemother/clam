/*
  nodes/heater.js — Electric Heater
  ─────────────────────────────────────────────────────────────────────────────
  Extends Load with thermal simulation: temperature rises while powered and
  falls when unpowered, providing an observable secondary effect beyond
  simple on/off state.

  This class demonstrates how a developer adds a custom node type:
    1. Extend a suitable base (Load, in this case).
    2. Declare static type, label, group, catalog.
    3. Override defaults() to add your extra fields.
    4. Override tick() to add per-frame behaviour (here: thermal update).
    5. Override reset() to clear your extra state.
    6. Call NodeRegistry.register(Heater) to make it available in the graph.

  Extra state
  ───────────
  temperature  number  — simulated temperature in °C (0–100 range, normalised)
  heatState    string  — 'cold' | 'warming' | 'hot'
  heatRate     number  — degrees per second when powered (default 8)
  coolRate     number  — degrees per second when unpowered (default 3)

  All power/capacitor/brownout logic is inherited from Load.
  States: inherited from Load ('off' | 'on' | 'brownout' | 'capacitor' | 'blown')
*/

class Heater extends Load {

    static type  = 'heater'
    static label = 'Heater'
    static group = 'Appliance'

    static catalog = [
        { key: 'heater-1kw', label: 'Heater 1kW',  watts: 1000, minVolts: 200 },
        { key: 'heater-2kw', label: 'Heater 2kW',  watts: 2000, minVolts: 205 },
        { key: 'heater-3kw', label: 'Heater 3kW',  watts: 3000, minVolts: 210 },
        { key: 'heater-oil', label: 'Oil Heater',   watts: 1500, minVolts: 200 },
    ]

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            // Override label default from Load
            label:       preset.label || 'Heater',
            watts:       preset.watts    ?? 1000,
            minVolts:    preset.minVolts ?? 200,
            // Thermal simulation
            temperature: 0,         // current temp in normalised °C (0–100)
            heatState:   'cold',    // 'cold' | 'warming' | 'hot'
            heatRate:    preset.heatRate ?? 8,   // °C/s while powered
            coolRate:    preset.coolRate ?? 3,   // °C/s while unpowered
        }
    }

    static configFields() {
        return [...super.configFields(), 'heatRate', 'coolRate']
    }

    // Power handling is fully inherited from Load.
    // We only need to add the thermal tick on top.
    static tick(panel, dt, graph) {
        // Capacitor logic (inherited)
        super.tick(panel, dt, graph)

        // Thermal update
        if (panel.state === 'on' || panel.state === 'capacitor') {
            panel.temperature = Math.min(100, panel.temperature + panel.heatRate * dt)
        } else {
            panel.temperature = Math.max(0, panel.temperature - panel.coolRate * dt)
        }

        panel.heatState = panel.temperature < 20  ? 'cold'
                        : panel.temperature < 60  ? 'warming'
                        : 'hot'
    }

    static reset(panel, graph) {
        panel.temperature = 0
        panel.heatState   = 'cold'
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Heater)
