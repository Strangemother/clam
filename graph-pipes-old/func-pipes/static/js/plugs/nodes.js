/*
  plugs-nodes.js
  ──────────────
  Node factories for the power plugs system.

  All nodes have 2 inbound pips + 2 outbound pips:
    pip index 0 = power channel
    pip index 1 = auxiliary / secondary channel

  Node types:
    battery  — power source; emits a configurable watts value on fire
    module   — power consumer; subtracts its usage from incoming watts,
               forwards the remainder on outbound pip 0
    meter    — display node; shows received power and passes it through
*/

function makeBatteryPanel(id) {
    return {
        type:            'battery',
        watts:           100,  // configurable output power
        state:           0,    // last emitted value
        connectionCount: 0,    // PWR outbound connections at last fire
        outputEdges:     [],   // [{ targetId, watts }] per-edge split table
        pipsInbound: [
            { label: id, index: 0 },
            { label: id, index: 1 },
        ],
        pipsOutbound: [
            { label: id, index: 0 },
            { label: id, index: 1 },
        ],
    }
}

function makeModulePanel(id) {
    return {
        type:         'module',
        usage:        20,  // watts consumed by this module
        powerIn:      0,   // sum of all inbound power sources
        powerUsed:    0,   // actual consumed (min of usage / available)
        powerOut:     0,   // remainder forwarded downstream
        state:        0,   // mirrors powerOut for compatibility
        powerSources: {},  // { [sourceId]: watts } — accumulated per sender
        pipsInbound: [
            { label: id, index: 0 },
            { label: id, index: 1 },
        ],
        pipsOutbound: [
            { label: id, index: 0 },
            { label: id, index: 1 },
        ],
    }
}

function makeMeterPanel(id) {
    return {
        type:         'meter',
        state:        0,   // sum of all inbound power sources
        peak:         0,   // highest combined value seen since last reset
        powerSources: {},  // { [sourceId]: watts } — accumulated per sender
        pipsInbound: [
            { label: id, index: 0 },
            { label: id, index: 1 },
        ],
        pipsOutbound: [
            { label: id, index: 0 },
            { label: id, index: 1 },
        ],
    }
}
