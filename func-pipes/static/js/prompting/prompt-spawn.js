/*
  prompt-spawn.js
  ─────────────────────────────────────────────────────────────────────────────
  Panel lifecycle: spawn, add by type / catalogue key, remove, reset.
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
        if (preset.type === 'text-input')   this._makeAndSpawn(makeTextInputPanel,   id, preset)
        if (preset.type === 'llm')          this._makeAndSpawn(makeLLMPanel,         id, preset)
        if (preset.type === 'text-display') this._makeAndSpawn(makeTextDisplayPanel, id, preset)
        if (preset.type === 'transform')    this._makeAndSpawn(makeTransformPanel,   id, preset)
    },

    addTextInput()   { const id = _uid + 1; this._makeAndSpawn(makeTextInputPanel,   id) },
    addLLM()         { const id = _uid + 1; this._makeAndSpawn(makeLLMPanel,         id) },
    addTextDisplay() { const id = _uid + 1; this._makeAndSpawn(makeTextDisplayPanel, id) },
    addTransform()   { const id = _uid + 1; this._makeAndSpawn(makeTransformPanel,   id) },

    removePanel(i) {
        const p = this.panels[i]
        // Abort any in-flight LLM request
        if (p.type === 'llm' && p._chat) p._chat.abort()
        // Emit null from all outbound pips so downstream nodes clear
        ;(p.pipsOutbound || []).forEach(pip => {
            this._emitFromPip(p, pip.index, null)
        })
        this.panels.splice(i, 1)
    },

    resetPanel(panel) {
        if (panel.type === 'text-input') {
            panel.input      = ''
            panel.messages   = []
            panel.lastOutput = null
            panel.state      = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'llm') {
            if (panel._chat) panel._chat.reset()
            panel._chat      = null
            panel.messages   = []
            panel.lastOutput = null
            panel.state      = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'text-display') {
            panel.messages = []
            panel.sources  = {}
            panel.state    = 'idle'
        }
        if (panel.type === 'transform') {
            panel.values   = {}
            panel.fnError  = null
            panel.state    = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
    },
}
