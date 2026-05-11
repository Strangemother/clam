/*
  nodes/heater.js — Electric Heater
  ─────────────────────────────────────────────────────────────────────────────
  Extends Load with thermal simulation and dynamic power draw. As the heater
  warms up its element draws progressively more power (up to the rated watts).
  A built-in thermostat (heatSwitch) trips the element off at maxTemp and
  resets it once the unit cools to resetTemp. A minimum standby draw
  (minWatts) is always present even when the element is off.

  This class demonstrates how a developer adds a custom node type:
    1. Extend a suitable base (Load, in this case).
    2. Declare static type, label, group, catalog.
    3. Override defaults() to add your extra fields.
    4. Override apply() to customise the power-draw amount.
    5. Override tick() to add per-frame behaviour (thermal update + thermostat).
    6. Override reset() to clear your extra state.
    7. Call NodeRegistry.register(Heater) to make it available in the graph.

  Extra state
  ───────────
  temperature   number  — simulated temperature in °C (0–maxTemp range)
  heatState     string  — 'cold' | 'warming' | 'hot'
  heatSwitch    bool    — thermostat: true = element on, false = tripped off
  currentWatts  number  — live draw (minWatts … watts), updated each tick
  heatRate      number  — °C/s when element is on (default 8)
  coolRate      number  — °C/s when element is off (default 3)
  maxTemp       number  — thermostat trip temperature in °C (default 100)
  resetTemp     number  — thermostat reset temperature in °C (default 70)
  minWatts      number  — standby draw always present, even when tripped (default 50)

  All power/capacitor/brownout logic is inherited from Load.
  States: inherited from Load ('off' | 'on' | 'brownout' | 'capacitor' | 'blown')
*/

class Heater extends Load {

    static type  = 'heater'
    static label = 'Heater'
    static group = 'Appliance'
    static dispatchDelay = 150  // faster than default — thermal events are time-sensitive

    static _defaultSpike() {
        return { enabled: true, percent: 30, duration: 3.8 }
    }

    static catalog = [
        { key: 'heater-1kw', label: 'Heater 1kW',  watts: 1000, minVolts: 200,
          spike: { enabled: true, percent: 30, duration: 0.8 } },
        { key: 'heater-2kw', label: 'Heater 2kW',  watts: 2000, minVolts: 205,
          spike: { enabled: true, percent: 35, duration: 0.9 } },
        { key: 'heater-3kw', label: 'Heater 3kW',  watts: 3000, minVolts: 210,
          spike: { enabled: true, percent: 40, duration: 1.0 } },
        { key: 'heater-oil', label: 'Oil Heater',   watts: 1500, minVolts: 200,
          spike: { enabled: true, percent: 15, duration: 0.5 } },
    ]

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            // Override label default from Load
            label:        preset.label    || 'Heater',
            watts:        preset.watts    ?? 1000,
            minVolts:     preset.minVolts ?? 200,
            // Thermal simulation
            temperature:  0,            // current temp in °C (0–maxTemp)
            heatState:    'cold',       // 'cold' | 'warming' | 'hot'
            heatSwitch:   true,         // thermostat: element enabled
            currentWatts: preset.minWatts ?? 50,  // live draw, starts at minimum
            heatRate:     preset.heatRate  ?? 8,  // °C/s while element is on
            coolRate:     preset.coolRate  ?? 3,  // °C/s while element is off
            maxTemp:      preset.maxTemp   ?? 100, // trip temperature
            resetTemp:    preset.resetTemp ?? 70,  // re-enable temperature
            minWatts:     preset.minWatts  ?? 50,  // standby draw (W)
            spike:        preset.spike ? { ...preset.spike } : { ...this._defaultSpike() },
        }
    }

    static configFields() {
        return [...super.configFields(), 'heatRate', 'coolRate', 'maxTemp', 'resetTemp', 'minWatts', 'spike']
    }

    // Override apply to use currentWatts (dynamic) instead of the fixed watts rating.
    static apply(panel, signal, graph) {
        if (panel.blown) return

        if (signal && signal.v > panel.maxVolts) {
            const prevState = panel.state
            panel.blown = true
            panel.state = 'blown'
            Heater.dispatch(panel, 'heater:blown', { volts: signal.v, maxVolts: panel.maxVolts })
            Heater.dispatch(panel, 'state:change', { from: prevState, to: 'blown' })
            graph.emit(panel, null)
            return
        }

        // We only need minWatts' worth of amps available to stay alive (standby).
        const minAmps  = panel.minWatts / NOMINAL_VOLTS
        const powered  = signal && signal.v >= panel.minVolts && signal.a >= minAmps

        const prevState = panel.state
        if (powered && prevState !== 'on' && prevState !== 'capacitor') NodeBase.startSpike(panel)
        const drawAmps = (panel.currentWatts / NOMINAL_VOLTS) * NodeBase.spikeMultiplier(panel)

        if (powered) {
            panel._lastGoodSignal = signal
            panel.state = 'on'
            graph.emit(panel, { v: signal.v, a: signal.a - drawAmps })
        } else if (!signal || signal.v <= 0) {
            if (panel.capacitance > 0 && panel.chargeWs > 0) {
                panel.state = 'capacitor'
                const held = panel._lastGoodSignal
                if (held) graph.emit(panel, { v: held.v, a: held.a - drawAmps })
                if (prevState !== 'capacitor')
                    Heater.dispatch(panel, 'heater:capacitor-failover', { chargeWs: panel.chargeWs })
            } else {
                panel.state = 'off'
                graph.emit(panel, null)
            }
        } else {
            panel.state = 'brownout'
            if (prevState !== 'brownout')
                Heater.dispatch(panel, 'heater:brownout', { volts: signal?.v, amps: signal?.a, minVolts: panel.minVolts })
            graph.emit(panel, null)
        }
        if (panel.state !== prevState)
            Heater.dispatch(panel, 'state:change', { from: prevState, to: panel.state })
    }

    static tick(panel, dt, graph) {
        // Capacitor logic (inherited)
        super.tick(panel, dt, graph)

        // Thermostat: trip element off at maxTemp, reset at resetTemp
        if (panel.heatSwitch && panel.temperature >= panel.maxTemp) {
            panel.heatSwitch = false
            Heater.dispatch(panel, 'thermostat:trip', { temp: panel.temperature })
        } else if (!panel.heatSwitch && panel.temperature <= panel.resetTemp) {
            panel.heatSwitch = true
            Heater.dispatch(panel, 'thermostat:reset', { temp: panel.temperature })
        }

        // Thermal update — only heat when element is on and the unit is powered
        const elementOn = panel.heatSwitch && (panel.state === 'on' || panel.state === 'capacitor')
        if (elementOn) {
            panel.temperature = Math.min(panel.maxTemp, panel.temperature + panel.heatRate * dt)
        } else {
            panel.temperature = Math.max(0, panel.temperature - panel.coolRate * dt)
        }

        const temp = +panel.temperature.toFixed(1)
        if (temp !== panel._lastCheckedTemp) {
            panel._lastCheckedTemp = temp
            Heater.throttle(panel, 'heater:temperature', { temp, max: panel.maxTemp })
        }

        // Dynamic draw: scale from minWatts (cold) up to rated watts (full temp)
        const heatFraction  = panel.temperature / panel.maxTemp
        const elementWatts  = panel.minWatts + (panel.watts - panel.minWatts) * heatFraction
        panel.currentWatts  = panel.heatSwitch ? elementWatts : panel.minWatts

        panel.heatState = panel.temperature < (panel.maxTemp * 0.2) ? 'cold'
                        : panel.temperature < (panel.maxTemp * 0.6) ? 'warming'
                        : 'hot'
        if (panel.heatState !== panel._lastHeatState) {
            Heater.dispatch(panel, 'heater:heat-state', { from: panel._lastHeatState, to: panel.heatState, temp: +panel.temperature.toFixed(1) })
            panel._lastHeatState = panel.heatState
        }

        // Re-apply with updated currentWatts so downstream sees the new amps
        // Only when the draw has meaningfully changed (>1 W) to avoid signal storms
        const prevWatts = panel._lastEmittedWatts ?? -1
        if (Math.abs(panel.currentWatts - prevWatts) > 1 &&
                panel.enabled !== false &&
                panel.signal !== undefined &&
                (panel.state === 'on' || panel.state === 'brownout')) {
            Heater.dispatch(panel, 'heater:draw-change', { from: +prevWatts.toFixed(1), to: +panel.currentWatts.toFixed(1) })
            panel._lastEmittedWatts = panel.currentWatts
            Heater.apply(panel, panel.signal, graph)
        }
    }

    static reset(panel, graph) {
        panel.temperature       = 0
        panel.heatState         = 'cold'
        panel._lastHeatState    = null
        panel._lastCheckedTemp  = null
        panel.heatSwitch        = true
        panel.currentWatts      = panel.minWatts ?? 50
        panel._lastEmittedWatts = -1
        Heater.dispatch(panel, 'heater:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(Heater)
