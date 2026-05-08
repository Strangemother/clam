/*
  power-spawn.js
  ─────────────────────────────────────────────────────────────────────────────
  Panel lifecycle: spawn, add by type/catalog, remove, reset, graph toggle.
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
        if (preset.type === 'gen')     this._makeAndSpawn(makeGenPanel,     id, preset)
        if (preset.type === 'breaker') this._makeAndSpawn(makeBreakerPanel, id, preset)
        if (preset.type === 'bulb')    this._makeAndSpawn(makeBulbPanel,    id, preset)
        if (preset.type === 'load')    this._makeAndSpawn(makeLoadPanel,    id, preset)
    },

    addGen()     { const id = _uid + 1; this._makeAndSpawn(makeGenPanel, id) },
    addBreaker() { const id = _uid + 1; this._makeAndSpawn(makeBreakerPanel, id) },
    addBulb()    { const id = _uid + 1; this._makeAndSpawn(makeBulbPanel, id) },
    addLoad()    { const id = _uid + 1; this._makeAndSpawn(makeLoadPanel, id) },
    addMeter()   { this._spawn(makePanel(makeMeterPanel(_uid + 1))) },

    removePanel(i) {
        const p = this.panels[i]
        if (p.type === 'gen' && p.live) this._emitPower(p, null)
        this.panels.splice(i, 1)
    },

    resetPanel(panel) {
        if (panel.type === 'gen') {
            panel.live = false; panel.state = 'off'; panel.overload = false
            this._emitPower(panel, null)
        }
        if (panel.type === 'breaker') {
            panel.tripped = false; panel.closed = true
            panel.signal = null; panel.powerSources = {}; panel.state = 'off'
            this._emitPower(panel, null)
        }
        if (panel.type === 'bulb') {
            panel.blown = false
            panel.signal = null; panel.powerSources = {}; panel.state = 'off'; panel.brightness = 0
            this._emitPower(panel, null)
        }
        if (panel.type === 'load') {
            panel.blown = false
            panel.signal = null; panel.powerSources = {}; panel._lastGoodSignal = null
            panel.state = 'off'; panel.chargeWs = 0
            this._emitPower(panel, null)
        }
        if (panel.type === 'meter') {
            panel.signal = null; panel.powerSources = {}; panel.state = 'off'
            panel.volts = 0; panel.amps = 0; panel.watts = 0
            this._emitPower(panel, null)
        }
    },

    toggleGraph() { this.graphRunning = !this.graphRunning },
}
