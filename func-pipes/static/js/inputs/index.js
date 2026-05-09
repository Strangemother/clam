/*
  inputs/index.js  (app shell)
  ────────────────────────────
  Thin entry point — bootstraps the Vue app and composes all method groups.

  Load order in inputs.html:
    nodes.js → inputs-spawn.js → inputs-signal.js → inputs-gamepad.js →
    inputs-wiring.js → inputs-persist.js → index.js
*/

const { createApp, nextTick } = Vue

let _uid = 0

// ── panel factory ─────────────────────────────────────────────────────────────
function makePanel(overrides = {}) {
    const id = ++_uid
    return Object.assign({ id, title: overrides.label || `Node ${id}` }, overrides)
}

// ── group catalogue helper ────────────────────────────────────────────────────
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
            panels:          [],
            catalogGroups:   catalogByGroup(),
            disconnectMode:  false,
            disconnectFirst: null,
        }
    },

    mounted() {
        this._startGamepadPoll()
    },

    beforeUnmount() {
        if (this._pollId) cancelAnimationFrame(this._pollId)
    },

    methods: {
        ...SpawnMethods,
        ...SignalMethods,
        ...GamepadMethods,
        ...WiringMethods,
        ...PersistMethods,
    },

}).mount('#app')
