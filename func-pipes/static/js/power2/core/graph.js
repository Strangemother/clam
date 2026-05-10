/*
  core/graph.js
  ─────────────────────────────────────────────────────────────────────────────
  Graph — central engine for the power-2 simulation.

  Responsibilities
  ────────────────
  • Signal propagation  : receive(), emit(), combineSources(), repropagateAll()
  • Generator draw BFS  : updateAllGenDraws(), computeGenDraw()
  • Ripple tick         : _tickRipple()
  • Animation frame     : startTick(), stopTick()
  • Pip wiring          : connect(), disconnect, edge inspector
  • Panel spawn/remove  : spawnPanel(), addType(), addFromCatalog(), remove(), reset()
  • Save / load         : saveLayout(), loadLayout(), exportJSON(), importJSON()

  The Graph holds a reference to the Vue app instance to access:
    app.panels          — reactive array of panel state objects
    app.graphRunning    — boolean (tick pauses when false)
    app.$refs           — for panel DOM position reads on save
    app.nextTick        — Vue's nextTick (injected at construction)

  Node behaviour (apply, tick, reset …) is fully delegated to the node class
  retrieved from NodeRegistry. The Graph itself has no per-type logic.
*/

class PowerGraph {

    /**
     * @param {Object} app      — Vue component instance (this inside Vue)
     * @param {Object} options
     * @param {Function} options.nextTick   — Vue's nextTick
     * @param {Function} options.stickAll   — dragsolo pip attachment helper
     * @param {Object}   options.dragHost   — DragSolo instance
     */
    constructor(app, { nextTick, stickAll, dragHost }) {
        this.app      = app
        this.nextTick = nextTick
        this.stickAll = stickAll
        this.dragHost = dragHost

        this._uid        = 0          // monotonically increasing panel ID counter
        this._tickId     = null       // rAF handle
        this._lastTick   = null       // timestamp of last rAF frame
        this._propagating = new Set() // cycle guard: panels currently mid-receive
    }

    // ── Conveniences ────────────────────────────────────────────────────────

    get panels()  { return this.app.panels }
    get running() { return this.app.graphRunning }

    _findPanel(id) {
        return this.panels.find(p => String(p.id) === String(id)) || null
    }

    // ══════════════════════════════════════════════════════════════════════════
    // SIGNAL PROPAGATION
    // ══════════════════════════════════════════════════════════════════════════

    /**
     * Deliver a signal from sourceId to panel, re-combine all sources, then
     * dispatch to the node class's apply() method.
     *
     * @param {Object}      panel      — reactive Vue panel state
     * @param {Object|null} signal     — { v, a } or null
     * @param {string|null} sourceId   — panel id of the upstream sender
     * @param {number}      inPipIndex — which inbound pip index was connected (default 0)
     */
    receive(panel, signal, sourceId = null, inPipIndex = 0) {
        if (this._propagating.has(panel.id)) return  // cycle guard
        this._propagating.add(panel.id)
        try {
        if (sourceId !== null) {
            if (signal === null) {
                delete panel.powerSources[sourceId]
            } else {
                panel.powerSources[sourceId] = signal
            }
        }

        // Let multi-input nodes (e.g. DecisionNode) know which pip just fired
        panel._lastInPip = inPipIndex

        const combined = this.combineSources(panel.powerSources)
        panel.signal   = combined

        const Cls = NodeRegistry.get(panel.type)
        if (!Cls) return

        if (panel.enabled === false) {
            panel.state = 'off'
            if (typeof Cls.onDisabled === 'function') {
                Cls.onDisabled(panel, this)
            } else {
                this.emit(panel, null)
            }
            return
        }

        Cls.apply(panel, combined, this)
        } finally {
            this._propagating.delete(panel.id)
        }
    }

    /**
     * Fold multiple upstream source signals into one combined { v, a }.
     * v = max voltage (dominant rail); a = sum of available amps.
     * Returns null when no live sources remain.
     */
    combineSources(sources) {
        const live = Object.values(sources).filter(s => s !== null && s.v > 0)
        if (!live.length) return null
        return {
            v: Math.max(...live.map(s => s.v)),
            a: live.reduce((sum, s) => sum + s.a, 0),
        }
    }

    /**
     * Forward signal from panel's outbound pip(s) to all connected targets.
     * Applies edge resistance/enable before delivery.
     */
    emit(panel, signal) {
        if (typeof pipesWalker === 'undefined') return
        const sourceId = String(panel.id)
        this._getOutboundConns(panel, 0).forEach(({ inLabel, inPip, connKey }) => {
            const target = this._findPanel(inLabel)
            if (target) {
                const transformed = EdgeStore2.applyEdge(signal, connKey)
                this.receive(target, transformed, sourceId, inPip ?? 0)
            }
        })
    }

    /**
     * Forward signal from a specific outbound pip index.
     * Used by multi-output nodes (e.g. DecisionNode) to route to a chosen output.
     * sourceId is `${panel.id}:${pipIndex}` so downstream nodes track each pip separately.
     *
     * @param {Object}      panel    — source panel
     * @param {number}      pipIndex — which outbound pip to emit from
     * @param {Object|null} signal   — { v, a } or null
     */
    emitTo(panel, pipIndex, signal) {
        if (typeof pipesWalker === 'undefined') return
        const sourceId = `${panel.id}:${pipIndex}`
        this._getOutboundConns(panel, pipIndex).forEach(({ inLabel, inPip, connKey }) => {
            const target = this._findPanel(inLabel)
            if (target) {
                const transformed = EdgeStore2.applyEdge(signal, connKey)
                this.receive(target, transformed, sourceId, inPip ?? 0)
            }
        })
    }

    /** Re-broadcast from every live generator after a topology change. */
    repropagateAll() {
        this.panels.forEach(p => {
            if (p.type === 'gen' && p.live) {
                this.emit(p, { v: p.volts, a: p.amps })
            }
        })
        this.updateAllGenDraws()
    }

    /** Re-push a fresh signal through one edge (after edge property change). */
    repropagateEdge(key) {
        const conn = pipesWalker?.connections?.[key]
        if (!conn) return

        const obj = conn.obj
        const isReceiverInbound  = obj.receiver?.direction === 'inbound'
        const senderDescriptor   = isReceiverInbound ? obj.sender   : obj.receiver
        const receiverDescriptor = isReceiverInbound ? obj.receiver : obj.sender

        const senderPanel   = this._findPanel(senderDescriptor?.label)
        const receiverPanel = this._findPanel(receiverDescriptor?.label)
        if (!senderPanel || !receiverPanel) return

        let rawSignal
        if (senderPanel.type === 'gen') {
            rawSignal = (senderPanel.live && senderPanel.state !== 'tripped')
                ? { v: senderPanel.volts, a: senderPanel.amps }
                : null
        } else {
            rawSignal = this.combineSources(senderPanel.powerSources ?? {})
        }

        const transformed = EdgeStore2.applyEdge(rawSignal, key)
        this.receive(receiverPanel, transformed, String(senderPanel.id))
    }

    // ── Routing helpers ──────────────────────────────────────────────────────

    /** Return all connections leaving panel's outbound pip at pipIndex. */
    _getOutboundConns(panel, pipIndex) {
        if (typeof pipesWalker === 'undefined') return []
        const result   = []
        const allConns = pipesWalker.connections

        pipesWalker.getConnections(String(panel.id)).forEach(conn => {
            const { sender, receiver } = conn.obj
            let outLabel = sender.label,   inLabel  = receiver.label
            let outPip   = sender.pipIndex ?? 0,   inPip = receiver.pipIndex ?? 0

            if (sender.direction === 'inbound') {
                outLabel = receiver.label; inLabel  = sender.label
                outPip   = receiver.pipIndex ?? 0; inPip = sender.pipIndex ?? 0
            }
            if (String(outLabel) !== String(panel.id)) return
            if (outPip !== pipIndex) return

            const connKey = Object.keys(allConns).find(k => allConns[k] === conn) || null
            result.push({ inLabel, inPip, connKey })
        })
        return result
    }

    // ══════════════════════════════════════════════════════════════════════════
    // GENERATOR DRAW (BFS)
    // ══════════════════════════════════════════════════════════════════════════

    /** Recompute draw watts/amps for every generator and rechargeable battery. */
    updateAllGenDraws() {
        this.panels.forEach(p => {
            if (p.type === 'gen' || p.type === 'series-bat') this.computeGenDraw(p)
        })
    }

    /**
     * BFS from a generator's outbound pip, summing load contributions.
     * Then adjust the generator's emitted signal based on load ratio.
     */
    computeGenDraw(gen) {
        const visited = new Set()
        const queue   = [String(gen.id)]
        let   totalW  = 0

        while (queue.length) {
            const nodeId = queue.shift()
            if (visited.has(nodeId)) continue
            visited.add(nodeId)

            const p = this._findPanel(nodeId)
            if (!p) continue

            const shareCount = Math.max(1, Object.keys(p.powerSources || {}).length)

            if (p.type === 'bulb' && (p.state === 'on' || p.state === 'dim')) {
                totalW += p.watts / shareCount
            }
            // Any Load (or Load subclass) that declares consumesWatts = true
            const Cls = NodeRegistry.get(p.type)
            if (Cls?.consumesWatts && (p.state === 'on' || p.state === 'capacitor')) {
                totalW += (p.currentWatts ?? p.watts) / shareCount
            }

            ;(p.pipsOutbound || []).forEach(pip => {
                this._getOutboundConns(p, pip.index).forEach(({ inLabel }) => {
                    if (!visited.has(String(inLabel))) queue.push(String(inLabel))
                })
            })
        }

        gen.drawWatts = +totalW.toFixed(1)
        gen.drawAmps  = gen.volts > 0 ? +(totalW / gen.volts).toFixed(2) : 0

        if (!gen.live) return

        const ratio = gen.drawAmps / gen.amps

        if (ratio > 1.3) {
            if (gen.state !== 'tripped') {
                gen.overload = true
                gen.state    = 'tripped'
                this.emit(gen, null)
            }
        } else if (ratio > 1.0) {
            const sagVolts = +(gen.volts * 0.85).toFixed(1)
            gen.overload   = true
            gen.state      = 'sag'
            this.emit(gen, { v: sagVolts, a: gen.amps })
        } else {
            if (gen.overload) {
                gen.overload = false
                gen.state    = 'on'
                this.emit(gen, { v: gen.volts, a: gen.amps })
            } else {
                gen.state = 'on'
            }
        }

        // Let the node class observe the final draw state (for events etc.)
        const Cls = NodeRegistry.get(gen.type)
        if (typeof Cls?.onDrawUpdated === 'function') Cls.onDrawUpdated(gen, this)
    }

    // ══════════════════════════════════════════════════════════════════════════
    // ANIMATION FRAME TICK
    // ══════════════════════════════════════════════════════════════════════════

    startTick() {
        const tick = (ts) => {
            this._tickId = requestAnimationFrame(tick)
            if (!this._lastTick) { this._lastTick = ts; return }
            const dt = Math.min((ts - this._lastTick) / 1000, 0.1)
            this._lastTick = ts

            if (!this.running) return

            this._tickRipple(dt)

            // Delegate per-node tick to each registered class
            this.panels.forEach(p => {
                const Cls = NodeRegistry.get(p.type)
                if (Cls) Cls.tick(p, dt, this)
            })

            // Recompute generator draw each frame (loads may have dynamic currentWatts)
            this.updateAllGenDraws()
        }
        this._tickId = requestAnimationFrame(tick)
    }

    stopTick() {
        if (this._tickId) cancelAnimationFrame(this._tickId)
    }

    // ── Ripple ───────────────────────────────────────────────────────────────

    _tickRipple(dt) {
        this.panels.forEach(p => {
            if (!p.ripple?.enabled) return

            p._rippleAccum = (p._rippleAccum || 0) + dt
            if (p._rippleAccum < p.ripple.interval) return
            p._rippleAccum  = 0
            p._rippleOffset = _rippleRandom(p.ripple.amount)

            if (p.type === 'gen' && p.live && p.state !== 'tripped') {
                const vOut = Math.max(1, p.volts + p._rippleOffset)
                this.emit(p, { v: vOut, a: p.amps })
            }

            if (p.type === 'load' && p.state === 'on' && p.signal) {
                const drawAmps  = p.watts / NOMINAL_VOLTS
                const ampJitter = _rippleRandom(p.ripple.amount / NOMINAL_VOLTS)
                const aOut      = Math.max(0, p.signal.a - drawAmps + ampJitter)
                this.emit(p, { v: p.signal.v, a: aOut })
            }

            if (p.type === 'converter' && p.state !== 'off' && p.signal) {
                const Cls = NodeRegistry.get('converter')
                if (Cls) Cls.apply(p, p.signal, this)
            }

            if (p.type === 'series-bat' && p.live && p.state !== 'dead' && p.state !== 'off' && p.signal !== undefined) {
                const Cls = NodeRegistry.get('series-bat')
                if (Cls) Cls.apply(p, p.signal, this)
            }
        })
    }

    /** Toggle ripple on a panel, initialising defaults on first use. */
    toggleRipple(panel) {
        if (!panel.ripple) this._initRipple(panel)
        panel.ripple.enabled = !panel.ripple.enabled
        if (!panel.ripple.enabled) {
            panel._rippleOffset = 0
            if (panel.type === 'gen' && panel.live) {
                this.emit(panel, { v: panel.volts, a: panel.amps })
                this.updateAllGenDraws()
            }
        }
    }

    rippleParamsChanged(panel) {
        if (!panel.ripple) return
        panel.ripple.amount   = Math.max(0.01, +panel.ripple.amount   || 0.1)
        panel.ripple.interval = Math.max(0.05, +panel.ripple.interval || 0.5)
    }

    _initRipple(panel) {
        const Cls = NodeRegistry.get(panel.type)
        const def = Cls?._defaultRipple?.() || { enabled: false, amount: 1, interval: 1 }
        panel.ripple        = { ...def }
        panel._rippleAccum   = 0
        panel._rippleOffset  = 0
    }

    // ══════════════════════════════════════════════════════════════════════════
    // PANEL SPAWN / REMOVE / RESET
    // ══════════════════════════════════════════════════════════════════════════

    /** Low-level: push a fully-built panel into panels[] and attach drag. */
    spawnPanel(panel) {
        this.panels.push(panel)
        this.nextTick(() => {
            const el = this.app.$refs[`panel-${panel.id}`]?.[0]
            if (el) {
                this.stickAll(el)
                this.dragHost.enable(el)
            }
        })
    }

    /** Create and spawn a node of the given type. */
    addType(type, preset = {}) {
        const id  = ++this._uid
        const raw = NodeRegistry.create(type, id, preset)
        if (!raw) return
        const panel = this._makePanel(raw)
        this.spawnPanel(panel)
    }

    /** Create and spawn a node from a catalog key. */
    addFromCatalog(key) {
        const entry = NodeRegistry.catalog().find(c => c.key === key)
        if (!entry) return
        this.addType(entry.type, entry)
    }

    /** Remove panel at index i and cut its upstream signal. */
    removePanel(i) {
        const p = this.panels[i]
        if (p.type === 'gen' && p.live) this.emit(p, null)
        this.panels.splice(i, 1)
    }

    /** Reset a panel to clean default state via its node class. */
    resetPanel(panel) {
        const Cls = NodeRegistry.get(panel.type)
        if (Cls) Cls.reset(panel, this)
    }

    /** Toggle the enabled/disabled off-switch on a panel and re-propagate. */
    toggleEnabled(panel) {
        panel.enabled = panel.enabled === false ? true : false

        // Sources (no inbound pips) must be handled directly — receive() is a no-op for them.
        const Cls = NodeRegistry.get(panel.type)
        if (!panel.pipsInbound?.length) {
            if (panel.enabled === false) {
                if (typeof Cls?.onDisabled === 'function') Cls.onDisabled(panel, this)
                else this.emit(panel, null)
            } else if (panel.live && panel.state !== 'tripped') {
                this.emit(panel, { v: panel.volts, a: panel.amps })
            }
        } else {
            this.receive(panel, panel.signal)
        }
        this.updateAllGenDraws()
    }

    // ── Internal factory ─────────────────────────────────────────────────────

    _makePanel(overrides = {}) {
        // Use id from defaults() if present, otherwise allocate a new one.
        const id = overrides.id ?? ++this._uid
        return Object.assign({ id, title: overrides.label || `Node ${id}` }, overrides)
    }

    // ══════════════════════════════════════════════════════════════════════════
    // WIRING — pip drag-and-drop, connect, disconnect, edge inspector
    // ══════════════════════════════════════════════════════════════════════════

    pipStartDrag(event, direction, pip) {
        event.target.classList.add('dragging')
        event.dataTransfer.clearData()
        event.dataTransfer.setData('text/plain', JSON.stringify({
            label: pip.label, direction, pipIndex: pip.index
        }))
    }

    pipEndDrag(event) {
        event.target.classList.remove('dragging')
        if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
    }

    pipDrop(event, direction, pip) {
        const sender   = JSON.parse(event.dataTransfer.getData('text/plain'))
        const receiver = { label: pip.label, direction, pipIndex: pip.index }
        this.connect(sender, receiver)
    }

    connect(sender, receiver) {
        const connKey = `${sender.label}-${sender.pipIndex ?? 0}-${receiver.label}-${receiver.pipIndex ?? 0}`
        document.dispatchEvent(new CustomEvent('connectnodes', {
            detail: {
                sender, receiver,
                line: { color: EdgeStore2.colorForEdge(connKey), width: 2 },
            }
        }))
        if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()

        // edge:connect — fired for both involved panels
        const _label = (id) => { const p = this._findPanel(id); return p ? `${p.type}:${p.id}` : String(id) }
        window.dispatchEvent(new CustomEvent('power2', { detail: {
            type: 'edge:connect',
            label: _label(sender.label),
            data: { from: _label(sender.label), fromPip: sender.pipIndex ?? 0,
                    to: _label(receiver.label),  toPip: receiver.pipIndex ?? 0 }
        }}))

        this.nextTick(() => {
            const conn = pipesWalker?.connections?.[connKey]
            if (conn) EdgeStore2.register(connKey, conn.obj)
            this.repropagateAll()
        })
    }

    /** Update edge properties and repropagate the affected wire. */
    updateEdge(key, props) {
        EdgeStore2.update(key, props)
        this.repropagateEdge(key)

        if (typeof clItems !== 'undefined' && typeof dispatchRequestDrawEvent !== 'undefined') {
            const conn = pipesWalker?.connections?.[key]
            if (conn) {
                const edge = EdgeStore2.get(key)
                conn.obj.line = conn.obj.line || {}
                conn.obj.line.color = EdgeStore2.colorForEdge(key)
                conn.obj.line.width = edge?.enabled === false ? 1 : 2
                clItems.layers.forEach(layer => {
                    if (layer.lines?.[key]) layer.lines[key].lineColor = conn.obj.line.color
                })
            }
            dispatchRequestDrawEvent()
        }
    }

    // ── Disconnect mode ──────────────────────────────────────────────────────

    disconnectPip(pip) {
        if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return
        const conns = pipesWalker.connections

        if (!this.app.disconnectFirst) {
            const hasConn = Object.values(conns).some(c => {
                const s = c.obj?.sender
                const r = c.obj?.receiver
                return (String(s?.label) === String(pip.label) && s?.pipIndex === pip.index)
                    || (String(r?.label) === String(pip.label) && r?.pipIndex === pip.index)
            })
            if (!hasConn) return
            this.app.disconnectFirst = { pip }
            return
        }

        const first = this.app.disconnectFirst
        this.app.disconnectFirst = null

        if (String(first.pip.label) === String(pip.label) && first.pip.index === pip.index) return

        const aLabel = String(first.pip.label), aIdx = first.pip.index
        const bLabel = String(pip.label),        bIdx = pip.index

        const toRemove = Object.keys(conns).filter(key => {
            const s = conns[key].obj?.sender
            const r = conns[key].obj?.receiver
            return (
                (String(s?.label) === aLabel && s?.pipIndex === aIdx &&
                 String(r?.label) === bLabel && r?.pipIndex === bIdx)
                ||
                (String(s?.label) === bLabel && s?.pipIndex === bIdx &&
                 String(r?.label) === aLabel && r?.pipIndex === aIdx)
            )
        })

        if (!toRemove.length) return

        toRemove.forEach(key => {
            const obj = conns[key].obj
            delete conns[key]
            if (typeof clItems !== 'undefined') {
                clItems.layers.forEach(layer => { delete layer.lines[key] })
            }

            const receiverDescriptor = obj?.receiver?.direction === 'inbound'
                ? obj.receiver
                : obj?.sender?.direction === 'inbound' ? obj.sender : null
            const senderDescriptor   = receiverDescriptor === obj?.receiver ? obj?.sender : obj?.receiver

            if (receiverDescriptor && senderDescriptor) {
                const receiverPanel = this._findPanel(receiverDescriptor.label)
                if (receiverPanel) {
                    this.receive(receiverPanel, null, String(senderDescriptor.label))
                }
            }

            // edge:disconnect — fired on the power2 bus
            const _label = (desc) => { const p = this._findPanel(desc?.label); return p ? `${p.type}:${p.id}` : String(desc?.label) }
            window.dispatchEvent(new CustomEvent('power2', { detail: {
                type: 'edge:disconnect',
                label: _label(senderDescriptor),
                data: { from: _label(senderDescriptor), fromPip: senderDescriptor?.pipIndex ?? 0,
                        to: _label(receiverDescriptor),  toPip: receiverDescriptor?.pipIndex ?? 0 }
            }}))
        })

        if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
    }

    // ── Edge inspector (two-click) ───────────────────────────────────────────

    selectEdgePip(pip) {
        if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return
        const conns = pipesWalker.connections

        if (!this.app.edgeFirst) {
            const hasConn = Object.values(conns).some(c => {
                const s = c.obj?.sender
                const r = c.obj?.receiver
                return (String(s?.label) === String(pip.label) && s?.pipIndex === pip.index)
                    || (String(r?.label) === String(pip.label) && r?.pipIndex === pip.index)
            })
            if (!hasConn) return
            this.app.edgeFirst = { pip }
            return
        }

        const first = this.app.edgeFirst
        this.app.edgeFirst = null

        if (String(first.pip.label) === String(pip.label) && first.pip.index === pip.index) return

        const aLabel = String(first.pip.label), aIdx = first.pip.index
        const bLabel = String(pip.label),        bIdx = pip.index

        const key = Object.keys(conns).find(k => {
            const s = conns[k].obj?.sender
            const r = conns[k].obj?.receiver
            return (
                (String(s?.label) === aLabel && s?.pipIndex === aIdx &&
                 String(r?.label) === bLabel && r?.pipIndex === bIdx)
                ||
                (String(s?.label) === bLabel && s?.pipIndex === bIdx &&
                 String(r?.label) === aLabel && r?.pipIndex === aIdx)
            )
        })

        if (!key) return
        this.app.activeEdge  = { key, edge: EdgeStore2.getOrCreate(key) }
        this.app.edgeMode    = false
    }

    // ══════════════════════════════════════════════════════════════════════════
    // PERSIST — save / load / export / import
    // ══════════════════════════════════════════════════════════════════════════

    static STORAGE_KEY = 'power2-backbone-layout'

    saveLayout() {
        const json = this._toJSON()
        try { localStorage.setItem(PowerGraph.STORAGE_KEY, json) } catch (e) {
            console.warn('[Graph] localStorage write failed', e)
        }
        console.info('[Graph] layout saved (%d nodes)', this.panels.length)
        return json
    }

    loadLayout(json = null) {
        const layout = json ? this._parseJSON(json) : this._loadFromStorage()
        if (!layout) { console.warn('[Graph] nothing to load'); return }
        this._restoreLayout(layout)
    }

    exportJSON() {
        const json = this._toJSON()
        const a    = document.createElement('a')
        a.href     = 'data:application/json,' + encodeURIComponent(json)
        a.download = 'power2-layout.json'
        a.click()
    }

    importJSON() {
        const input   = document.createElement('input')
        input.type    = 'file'
        input.accept  = '.json,application/json'
        input.onchange = e => {
            const file = e.target.files[0]
            if (!file) return
            const reader = new FileReader()
            reader.onload = ev => this.loadLayout(ev.target.result)
            reader.readAsText(file)
        }
        input.click()
    }

    // ── Serialise ────────────────────────────────────────────────────────────

    _toJSON() {
        return JSON.stringify(this._toObject(), null, 2)
    }

    _toObject() {
        const nodes = this.panels.map(p => {
            const Cls    = NodeRegistry.get(p.type)
            const fields = Cls ? Cls.configFields() : ['label']
            const config = {}
            fields.forEach(f => { config[f] = p[f] })
            return { id: p.id, type: p.type, title: p.title, config, pos: this._readPos(p.id) }
        })

        const connections = this._readConnections()
        return { nodes, connections, edges: EdgeStore2.toJSON() }
    }

    _readPos(panelId) {
        const ref = this.app.$refs[`panel-${panelId}`]
        const el  = Array.isArray(ref) ? ref[0] : ref
        if (!el) return { left: '20px', top: '20px' }
        return { left: el.style.left || '20px', top: el.style.top || '20px' }
    }

    _readConnections() {
        if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return []
        return Object.values(pipesWalker.connections).map(c => c.obj).filter(Boolean)
    }

    _parseJSON(json) {
        try { return JSON.parse(json) } catch (e) {
            console.error('[Graph] invalid JSON', e)
            return null
        }
    }

    _loadFromStorage() {
        try {
            const raw = localStorage.getItem(PowerGraph.STORAGE_KEY)
            return raw ? JSON.parse(raw) : null
        } catch (e) {
            console.error('[Graph] corrupt localStorage entry', e)
            return null
        }
    }

    // ── Restore ──────────────────────────────────────────────────────────────

    async _restoreLayout(layout) {
        if (!layout?.nodes) return

        this._clearAll()
        await this.nextTick()

        const maxId = Math.max(0, ...layout.nodes.map(n => n.id))

        for (const node of layout.nodes) {
            // Rewind uid so makePanel assigns the original saved id.
            this._uid = node.id - 1

            const raw = NodeRegistry.create(node.type, node.id, node.config || {})
            if (!raw) continue
            // raw.id is already set to node.id by NodeBase.defaults()
            const panel = this._makePanel(raw)
            if (node.title && node.title !== panel.title) panel.title = node.title

            // Carry live state so generators re-power their network after restore.
            if (node.type === 'gen' && node.config?.live) {
                panel.live  = true
                panel.state = 'on'
            }

            this.spawnPanel(panel)
        }
        this._uid = maxId

        await this.nextTick()
        await this.nextTick()   // wait for nextTick callbacks inside spawnPanel

        // Place panels at saved positions
        layout.nodes.forEach(node => {
            const ref = this.app.$refs[`panel-${node.id}`]
            const el  = Array.isArray(ref) ? ref[0] : ref
            if (el && node.pos) {
                el.style.left = node.pos.left
                el.style.top  = node.pos.top
            }
        })

        // Rewire
        for (const obj of (layout.connections || [])) {
            const sEl = document.getElementById(`${obj.sender.label}-${obj.sender.direction}-${obj.sender.pipIndex}`)
            const rEl = document.getElementById(`${obj.receiver.label}-${obj.receiver.direction}-${obj.receiver.pipIndex}`)
            if (sEl && rEl) {
                this.connect(obj.sender, obj.receiver)
            } else {
                console.warn('[Graph] skipping connection — pip element not found', obj)
            }
        }

        if (layout.edges) {
            await this.nextTick()
            EdgeStore2.fromJSON(layout.edges)
        }

        await this.nextTick()
        this.repropagateAll()
        if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
    }

    _clearAll() {
        this.panels.forEach(p => { if (p.type === 'gen' && p.live) this.emit(p, null) })
        this.panels.splice(0)
        this.app.activeEdge = null

        for (const k in EdgeStore2.store) delete EdgeStore2.store[k]

        if (typeof pipesWalker !== 'undefined' && pipesWalker.connections) {
            for (const k in pipesWalker.connections) delete pipesWalker.connections[k]
        }
        if (typeof clItems !== 'undefined') {
            clItems.layers.forEach(layer => { layer.lines = {} })
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        }
    }
}

// ── Ripple helper (module-private) ───────────────────────────────────────────
function _rippleRandom(amount) {
    return (Math.random() * 2 - 1) * amount
}
