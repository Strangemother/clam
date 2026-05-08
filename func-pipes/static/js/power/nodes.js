/*
  power-nodes.js
  ──────────────
  Node factories and component catalogue for the power backbone system.

  Power signal: { v: volts, a: amps_available }  |  null (no power)

  Node types
  ──────────
    gen     — generator / power source. No inbound pip.
    breaker — circuit breaker or relay. Manual open/close toggle.
    bulb    — resistive lamp. Visual brightness. No outbound pip (sink).
    load    — generic configurable load. Optional capacitance buffer.
    meter   — instrument; reads V/A/W and passes signal through unchanged.

  Pip layout
  ──────────
    All nodes have pipsInbound[0] and pipsOutbound[0], except:
      gen  → no inbound pips  (source only)
      bulb → no outbound pips (sink only)
*/

// ── rated voltage assumed for W→A conversion ───────────────────────────────
const NOMINAL_VOLTS = 240

// ── component catalogue ─────────────────────────────────────────────────────
const COMPONENT_CATALOG = [
    // Sources
    { key: 'wall-outlet',  group: 'Source',   type: 'gen',     label: 'Wall Outlet',   volts: 240, amps: 13 },
    { key: 'generator',    group: 'Source',   type: 'gen',     label: 'Generator',     volts: 240, amps: 30 },
    { key: 'ship-reactor', group: 'Source',   type: 'gen',     label: 'Ship Reactor',  volts: 240, amps: 120 },
    { key: 'battery-12v',  group: 'Source',   type: 'gen',     label: 'Battery 12V',   volts: 12,  amps: 20 },
    { key: 'battery-48v',  group: 'Source',   type: 'gen',     label: 'Battery 48V',   volts: 48,  amps: 30 },
    // Breakers
    { key: 'breaker-6a',   group: 'Control',  type: 'breaker', label: 'Breaker  6A',   ratingAmps: 6 },
    { key: 'breaker-13a',  group: 'Control',  type: 'breaker', label: 'Breaker 13A',   ratingAmps: 13 },
    { key: 'breaker-30a',  group: 'Control',  type: 'breaker', label: 'Breaker 30A',   ratingAmps: 30 },
    { key: 'relay',        group: 'Control',  type: 'breaker', label: 'Relay',          ratingAmps: 10 },
    // Lights
    { key: 'led-5w',       group: 'Light',    type: 'bulb',    label: 'LED  5W',       watts: 5 },
    { key: 'bulb-40w',     group: 'Light',    type: 'bulb',    label: 'Bulb  40W',     watts: 40 },
    { key: 'bulb-60w',     group: 'Light',    type: 'bulb',    label: 'Bulb  60W',     watts: 60 },
    { key: 'bulb-100w',    group: 'Light',    type: 'bulb',    label: 'Bulb 100W',     watts: 100 },
    // Loads
    { key: 'fan',          group: 'Load',     type: 'load',    label: 'Fan',           watts: 25,   minVolts: 200 },
    { key: 'pump',         group: 'Load',     type: 'load',    label: 'Pump',          watts: 180,  minVolts: 210 },
    { key: 'motor-sm',     group: 'Load',     type: 'load',    label: 'Motor (sm)',    watts: 370,  minVolts: 215 },
    { key: 'motor-lg',     group: 'Load',     type: 'load',    label: 'Motor (lg)',    watts: 1500, minVolts: 220 },
    { key: 'heater',       group: 'Load',     type: 'load',    label: 'Heater',        watts: 1000, minVolts: 200 },
    { key: 'console',      group: 'Load',     type: 'load',    label: 'Console',       watts: 50,   minVolts: 180, capacitance: 20 },
    { key: 'ups',          group: 'Load',     type: 'load',    label: 'UPS Buffer',    watts: 5,    minVolts: 190, capacitance: 600 },
]

// ── factories ────────────────────────────────────────────────────────────────

function makeGenPanel(id, p = {}) {
    return {
        type:      'gen',
        label:     p.label || 'Generator',
        volts:     p.volts || 240,
        amps:      p.amps  || 13,
        live:      false,
        state:     'off',    // 'off' | 'on' | 'sag' | 'tripped'
        overload:  false,    // true when draw exceeded rating at last compute
        drawWatts: 0,
        drawAmps:  0,
        pipsInbound:  [],
        pipsOutbound: [{ label: id, index: 0 }],
    }
}

function makeBreakerPanel(id, p = {}) {
    return {
        type:         'breaker',
        label:        p.label      || 'Breaker',
        ratingAmps:   p.ratingAmps || 16,
        closed:       true,
        tripped:      false,
        signal:       null,
        powerSources: {},   // { [sourceId]: {v,a} | null }
        state:        'off',
        pipsInbound:  [{ label: id, index: 0 }],
        pipsOutbound: [{ label: id, index: 0 }],
    }
}

function makeBulbPanel(id, p = {}) {
    return {
        type:         'bulb',
        label:        p.label    || 'Bulb',
        watts:        p.watts    || 60,
        maxVolts:     p.maxVolts || (p.volts ? p.volts * 1.2 : 288),
        signal:       null,
        powerSources: {},
        state:        'off',
        brightness:   0,
        blown:        false,
        pipsInbound:  [{ label: id, index: 0 }],
        pipsOutbound: [{ label: id, index: 0 }],
    }
}

function makeLoadPanel(id, p = {}) {
    return {
        type:            'load',
        label:           p.label       || 'Load',
        watts:           p.watts       || 100,
        minVolts:        p.minVolts    || 200,
        maxVolts:        p.maxVolts    || (p.minVolts ? p.minVolts * 1.25 : 300),
        capacitance:     p.capacitance || 0,
        chargeWs:        0,
        signal:          null,        powerSources:    {},        _lastGoodSignal: null,
        state:           'off',   // 'off' | 'on' | 'brownout' | 'capacitor' | 'blown'
        blown:           false,
        pipsInbound:  [{ label: id, index: 0 }],
        pipsOutbound: [{ label: id, index: 0 }],
    }
}

function makeMeterPanel(id) {
    return {
        type:         'meter',
        signal:       null,
        powerSources: {},
        volts:  0,
        amps:   0,
        watts:  0,
        state:  'off',    // 'off' | 'on'
        pipsInbound:  [{ label: id, index: 0 }],
        pipsOutbound: [{ label: id, index: 0 }],
    }
}
