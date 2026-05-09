/*
  inputs-persist.js
  ─────────────────────────────────────────────────────────────────────────────
  Save / restore layout to localStorage or JSON file.
  Mirrors power-persist.js; no edge resistance data to store.
*/

const STORAGE_KEY = 'inputs-layout-v1'

const PersistMethods = {

    saveLayout() {
        const json = this._toJSON()
        localStorage.setItem(STORAGE_KEY, json)
        console.info('InputsSave: layout saved (%d nodes)', this.panels.length)
    },

    exportJSON() {
        const json = this._toJSON()
        const a    = document.createElement('a')
        a.href     = 'data:application/json,' + encodeURIComponent(json)
        a.download = 'inputs-layout.json'
        a.click()
    },

    loadLayout(json = null) {
        const src    = json ?? localStorage.getItem(STORAGE_KEY)
        if (!src) { console.warn('InputsSave: nothing to load'); return }
        const layout = JSON.parse(src)
        this._restoreLayout(layout)
    },

    importJSON() {
        const input  = document.createElement('input')
        input.type   = 'file'
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

    // ── internal ──────────────────────────────────────────────────────

    _toJSON() {
        const nodes = this.panels.map(p => {
            const ref = this.$refs[`panel-${p.id}`]
            const el  = Array.isArray(ref) ? ref[0] : ref
            const pos = el ? { left: el.style.left, top: el.style.top } : null
            let config
            if (p.type === 'gamepad') {
                config = { gamepadIndex: p.gamepadIndex }
            } else if (p.type === 'compute') {
                config = {
                    label:      p.label,
                    inputs:     p.pipsInbound.map(pip  => ({ name: pip.name,  index: pip.index })),
                    outputs:    p.pipsOutbound.map(pip => ({ name: pip.name,  index: pip.index })),
                    fnSrc:      p.fnSrc,
                    gatePip:    p.gatePip,
                    gateThresh: p.gateThresh,
                    gateMode:   p.gateMode,
                }
            } else {
                config = { label: p.label }
            }
            return { id: p.id, type: p.type, title: p.title || p.label, config, pos }
        })

        const connections = []
        if (typeof pipesWalker !== 'undefined' && pipesWalker.connections) {
            Object.values(pipesWalker.connections).forEach(conn => {
                connections.push({ sender: conn.obj.sender, receiver: conn.obj.receiver })
            })
        }

        return JSON.stringify({ nodes, connections }, null, 2)
    },

    async _restoreLayout(layout) {
        if (!layout?.nodes) return

        this._clearAll()
        await nextTick()

        const factoryMap = { gamepad: makeGamepadPanel, value: makeValuePanel, compute: makeComputePanel }
        const maxId = Math.max(0, ...layout.nodes.map(n => n.id))

        for (const node of layout.nodes) {
            _uid = node.id - 1
            const factory = factoryMap[node.type]
            if (!factory) continue
            const panel = makePanel(factory(node.id, node.config || {}))
            if (node.title) panel.title = node.title
            this._spawn(panel)
        }
        _uid = maxId

        await nextTick()
        await nextTick()

        layout.nodes.forEach(node => {
            const ref = this.$refs[`panel-${node.id}`]
            const el  = Array.isArray(ref) ? ref[0] : ref
            if (el && node.pos) {
                el.style.left = node.pos.left
                el.style.top  = node.pos.top
            }
        })

        for (const obj of (layout.connections || [])) {
            const sEl = document.getElementById(`${obj.sender.label}-${obj.sender.direction}-${obj.sender.pipIndex}`)
            const rEl = document.getElementById(`${obj.receiver.label}-${obj.receiver.direction}-${obj.receiver.pipIndex}`)
            if (sEl && rEl) {
                this.connect(obj.sender, obj.receiver)
            } else {
                console.warn('InputsSave: skipping connection — pip not found', obj)
            }
        }

        await nextTick()
        this._repropagateAll()
        if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
    },

    _clearAll() {
        this.panels.splice(0)
        if (typeof pipesWalker !== 'undefined' && pipesWalker.connections) {
            for (const k in pipesWalker.connections) delete pipesWalker.connections[k]
        }
        if (typeof clItems !== 'undefined') {
            clItems.layers.forEach(layer => { layer.lines = {} })
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        }
    },
}
