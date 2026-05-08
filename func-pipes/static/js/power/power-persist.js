/*
  power-persist.js
  ─────────────────────────────────────────────────────────────────────────────
  Save / restore layout: localStorage, JSON export/import, full rebuild.
*/

const PersistMethods = {

    // Persist the current layout to localStorage and return a JSON string.
    saveLayout() {
        const json = PowerSave.save(this.panels, this.$refs, EdgeStore.toJSON())
        console.info('PowerSave: layout saved (%d nodes)', this.panels.length)
        return json
    },

    // Trigger a JSON file download of the current layout.
    exportJSON() {
        const json = PowerSave.toJSON(this.panels, this.$refs, EdgeStore.toJSON())
        const a    = document.createElement('a')
        a.href     = 'data:application/json,' + encodeURIComponent(json)
        a.download = 'power-layout.json'
        a.click()
    },

    // Load from localStorage (json = null) or from a supplied JSON string.
    loadLayout(json = null) {
        const layout = json ? PowerSave.parseJSON(json) : PowerSave.loadFromStorage()
        if (!layout) { console.warn('PowerSave: nothing to load'); return }
        this._restoreLayout(layout)
    },

    // Open a file picker and load the chosen JSON file.
    importJSON() {
        const input = document.createElement('input')
        input.type  = 'file'
        input.accept = '.json,application/json'
        input.onchange = e => {
            const file = e.target.files[0]
            if (!file) return
            const reader = new FileReader()
            reader.onload = ev => this.loadLayout(ev.target.result)
            reader.readAsText(file)
        }
        input.click()
    },

    // ── internal: wipe everything then rebuild from a layout object ──

    async _restoreLayout(layout) {
        if (!layout?.nodes) return

        // 1. Tear down current state
        this._clearAll()
        await nextTick()  // Vue removes old panel DOMs

        // 2. Spawn panels with their original IDs so pip/connection labels match
        const factoryMap = {
            gen:     makeGenPanel,
            breaker: makeBreakerPanel,
            bulb:    makeBulbPanel,
            load:    makeLoadPanel,
        }
        const maxId = Math.max(0, ...layout.nodes.map(n => n.id))

        for (const node of layout.nodes) {
            // Temporarily rewind _uid so makePanel assigns the saved id
            _uid = node.id - 1
            let rawData
            if (node.type === 'meter') {
                rawData = makeMeterPanel(node.id)
            } else {
                const factory = factoryMap[node.type]
                if (!factory) continue
                rawData = factory(node.id, node.config)
            }
            const panel = makePanel(rawData)
            if (node.title && node.title !== panel.title) panel.title = node.title
            // Carry live state for generators — needed for repropagation after restore
            if (node.type === 'gen' && node.config?.live) {
                panel.live  = true
                panel.state = 'on'
            }
            this._spawn(panel)
        }
        _uid = maxId

        // 3. Wait for Vue to flush new DOMs AND for _spawn's nextTick callbacks
        //    (stickAll + dragHost.enable) to finish before we touch positions or
        //    fire connectnodes (getTip needs pip elements to exist in the DOM).
        await nextTick()  // Vue renders panel elements
        await nextTick()  // _spawn's nextTick callbacks (stickAll, dragHost.enable) run

        // 4. Place panels at their saved positions (after stickAll so we win)
        layout.nodes.forEach(node => {
            const ref = this.$refs[`panel-${node.id}`]
            const el  = Array.isArray(ref) ? ref[0] : ref
            if (el && node.pos) {
                el.style.left = node.pos.left
                el.style.top  = node.pos.top
            }
        })

        // 5. Rewire connections — pip DOM elements are guaranteed ready now
        for (const obj of (layout.connections || [])) {
            // Verify both pip elements exist before dispatching (avoids silent null errors)
            const sEl = document.getElementById(`${obj.sender.label}-${obj.sender.direction}-${obj.sender.pipIndex}`)
            const rEl = document.getElementById(`${obj.receiver.label}-${obj.receiver.direction}-${obj.receiver.pipIndex}`)
            if (sEl && rEl) {
                this.connect(obj.sender, obj.receiver)
            } else {
                console.warn('PowerSave: skipping connection — pip element not found', obj)
            }
        }

        // 5b. Restore edge properties (must be after connect() registers fresh entries)
        if (layout.edges) {
            await nextTick()
            EdgeStore.fromJSON(layout.edges)
        }

        // 6. Let connect's nextTick(_repropagateAll) settle, then run a final propagation
        //    so live generators power their downstream nodes immediately.
        await nextTick()
        this._repropagateAll()
        if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
    },

    // Remove all panels and clear the wire canvas.
    _clearAll() {
        this.panels.forEach(p => { if (p.type === 'gen' && p.live) this._emitPower(p, null) })
        this.panels.splice(0)
        this.activeEdge = null
        // Clear edge store
        for (const k in EdgeStore.store) delete EdgeStore.store[k]
        // pipeData is IIFE-scoped inside pipes-runtime.js and not exported.
        // pipesWalker.connections holds the same object reference, so clearing that
        // also clears pipeData.connections.
        if (typeof pipesWalker !== 'undefined' && pipesWalker.connections) {
            for (const k in pipesWalker.connections) delete pipesWalker.connections[k]
        }
        // Clear canvas line cache so no ghost wires remain
        if (typeof clItems !== 'undefined') {
            clItems.layers.forEach(layer => { layer.lines = {} })
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        }
    },
}
