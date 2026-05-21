/*
  inputs-spawn.js
  ─────────────────────────────────────────────────────────────────────────────
  Panel lifecycle: spawn, add by type/catalog, remove, reset.
*/

const SpawnMethods = {

    _spawn(panel) {
        this.panels.push(panel)
        nextTick(() => {
            const el = this.$refs[`panel-${panel.id}`][0]
            stickAll(el)
            dragHost.enable(el)
        })
    },

    _makeAndSpawn(factory, id, preset) {
        this._spawn(makePanel(factory(id, preset)))
    },

    addFromCatalog(key) {
        const preset = COMPONENT_CATALOG.find(c => c.key === key)
        if (!preset) return
        const id = _uid + 1
        if (preset.type === 'gamepad') this._makeAndSpawn(makeGamepadPanel, id, preset)
        if (preset.type === 'value')   this._makeAndSpawn(makeValuePanel,   id, preset)
        if (preset.type === 'compute') this._makeAndSpawn(makeComputePanel, id, preset)
    },

    addGamepad() { const id = _uid + 1; this._makeAndSpawn(makeGamepadPanel, id) },
    addValue()   { const id = _uid + 1; this._makeAndSpawn(makeValuePanel,   id) },
    addCompute() { const id = _uid + 1; this._makeAndSpawn(makeComputePanel, id) },

    removePanel(i) {
        const p = this.panels[i]
        // Emit null from all pips so downstream nodes clear
        ;(p.pipsOutbound || []).forEach(pip => {
            this._emitFromPip(p, pip.index, null)
        })
        this.panels.splice(i, 1)
    },

    resetPanel(panel) {
        if (panel.type === 'gamepad') {
            panel.state = 'idle'
            panel.currentValues = {}
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'value') {
            panel.value   = null
            panel.sources = {}
            panel.state   = 'idle'
        }
        if (panel.type === 'compute') {
            panel.values  = {}
            panel.sources = {}
            panel.fnError = null
            panel.state   = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
    },
}
