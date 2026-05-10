/*
  power-index.js  (app shell)
  ────────────────────────────
  Thin entry point — bootstraps the Vue app and composes method groups
  defined in the sibling files:

    power-spawn.js   — panel lifecycle (spawn, add, remove, reset)
    power-gen.js     — generator toggle, params, BFS draw, overload
    power-signal.js  — receive, combine, emit, routing, re-propagate
                       (also: toggleBreaker, loadParamsChanged)
    power-nodes.js   — _applyBreaker/Bulb/Load/Meter, chargePercent
    power-tick.js    — rAF capacitor tick
    power-wiring.js  — pip drag-drop, connect, edge update, disconnect mode
    power-persist.js — save/load/export/import, _restoreLayout, _clearAll

  Load order in power.html:
    nodes.js → power-edges.js → power-save.js →
    power-spawn.js → power-gen.js → power-signal.js → power-nodes.js →
    power-tick.js → power-wiring.js → power-persist.js → index.js
*/

const { createApp, nextTick } = Vue

let _uid = 0
let _lastTick = null

// ── panel factory ────────────────────────────────────────────────────────────
function makePanel(overrides = {}) {
    const id = ++_uid
    return Object.assign({ id, title: overrides.label || `Node ${id}` }, overrides)
}

// ── group catalogue items ─────────────────────────────────────────────────────
function catalogByGroup() {
    const groups = {}
    COMPONENT_CATALOG.forEach(c => {
        if (!groups[c.group]) groups[c.group] = []
        groups[c.group].push(c)
    })
    return groups
}

dragHost = new DragSolo()

createApp({

    data() {
        return {
            graphRunning: true,
            panels:       [],
            catalogGroups: catalogByGroup(),
            disconnectMode:  false,
            disconnectFirst: null,
            edgeMode:        false,
            edgeFirst:       null,
            activeEdge:      null,
            EdgeWireTypes:   EdgeStore.WIRE_TYPES,
        }
    },

    mounted()        { this._startTick() },
    beforeUnmount()  { if (this._tickId) cancelAnimationFrame(this._tickId) },

    methods: {
        ...SpawnMethods,
        ...GenMethods,
        ...SignalMethods,
        ...NodeMethods,
        ...ConverterMethods,
        ...RippleMethods,
        ...TickMethods,
        ...WiringMethods,
        ...PersistMethods,
    },

}).mount('#app')
