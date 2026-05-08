/*
  power-index.js
  ──────────────
  Vue app + simulation engine for the power backbone page.

  Design principles
  ─────────────────
  • Event-driven propagation: signals travel downstream only when something
    changes (node toggled, wire connected, load updated). No constant polling.
  • Constant-load model: once a node is powered it stays in that state until
    a new signal arrives. The graph is "live" but quiet when stable.
  • Realtime tick (rAF): used exclusively for capacitor charge/drain.
    Nothing else runs on the tick.
  • Auto-propagate on connect: when a wire is drawn, all live generators
    re-broadcast so newly connected nodes receive power immediately.

  Power signal: { v: volts, a: amps_available }  |  null (no power)

  Amp subtraction model
  ─────────────────────
  Each consuming node subtracts its own draw from the available amps
  then forwards the remainder downstream:
      out.a = in.a - (watts / NOMINAL_VOLTS)
  If out.a < 0 the downstream node sees insufficient current and enters
  brownout / off state. Upstream is NOT notified (no backpropagation).
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

        /* ── spawn ──────────────────────────────────────────────────── */

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

        /* ── generator control ──────────────────────────────────────── */

        toggleGen(panel) {
            if (panel.state === 'tripped') {
                // Reset a tripped generator — goes to off, user must re-enable.
                panel.overload = false
                panel.live     = false
                panel.state    = 'off'
                this._emitPower(panel, null)
                this._updateAllGenDraws()
                return
            }
            panel.live  = !panel.live
            panel.state = panel.live ? 'on' : 'off'
            this._emitPower(panel, panel.live ? { v: panel.volts, a: panel.amps } : null)
            this._updateAllGenDraws()
        },

        // Called when V or A is changed on a live gen — re-broadcast.
        genParamsChanged(panel) {
            if (panel.live && panel.state !== 'tripped') {
                // Recover from sag if params were raised
                panel.overload = false
                this._emitPower(panel, { v: panel.volts, a: panel.amps })
                this._updateAllGenDraws()
            }
        },

        /* ── breaker control ────────────────────────────────────────── */

        toggleBreaker(panel) {
            if (panel.tripped) {
                panel.tripped = false
                panel.closed  = false
            } else {
                panel.closed = !panel.closed
            }
            this._applyBreaker(panel, panel.signal)
            this._updateAllGenDraws()
        },

        /* ── load: live watt/threshold changes ──────────────────────── */

        loadParamsChanged(panel) {
            if (panel.signal !== undefined) this._applyLoad(panel, panel.signal)
            this._updateAllGenDraws()
        },

        /* ── core receive ───────────────────────────────────────────── */

        /*
          receive(panel, signal, sourceId)
          Accumulates per-source signals, then re-derives a combined signal
          and applies the node's processor.

          Combined from parallel sources:
            v = max voltage across live sources  (dominant rail)
            a = sum of available amps            (parallel capacity)
          When signal is null, that source's contribution is removed.
        */
        receive(panel, signal, sourceId = null) {
            if (sourceId !== null) {
                if (signal === null) {
                    delete panel.powerSources[sourceId]
                } else {
                    panel.powerSources[sourceId] = signal
                }
            }

            const combined = this._combineSources(panel.powerSources)
            panel.signal   = combined

            if (panel.type === 'breaker') this._applyBreaker(panel, combined)
            if (panel.type === 'bulb')    this._applyBulb(panel, combined)
            if (panel.type === 'load')    this._applyLoad(panel, combined)
            if (panel.type === 'meter')   this._applyMeter(panel, combined)
        },

        /*
          _combineSources — fold all live source signals into one.
          Returns null when no sources remain.
        */
        _combineSources(sources) {
            const live = Object.values(sources).filter(s => s !== null && s.v > 0)
            if (!live.length) return null
            return {
                v: Math.max(...live.map(s => s.v)),
                a: live.reduce((sum, s) => sum + s.a, 0),
            }
        },

        /* ── node processors ────────────────────────────────────────── */

        _applyBreaker(panel, signal) {
            if (!signal || signal.v <= 0) {
                panel.state = 'off'
                this._emitPower(panel, null)
                return
            }
            if (panel.tripped) {
                panel.state = 'tripped'
                this._emitPower(panel, null)
                return
            }
            if (!panel.closed) {
                panel.state = 'open'
                this._emitPower(panel, null)
                return
            }
            // Auto-trip on over-current
            if (signal.a > panel.ratingAmps) {
                panel.tripped = true
                panel.state   = 'tripped'
                this._emitPower(panel, null)
                return
            }
            panel.state = 'closed'
            this._emitPower(panel, { v: signal.v, a: signal.a })
        },

        _applyBulb(panel, signal) {
            // Once blown, ignore all signals until manually reset.
            if (panel.blown) return

            if (!signal || signal.v <= 0 || signal.a <= 0) {
                panel.state = 'off'; panel.brightness = 0
                this._emitPower(panel, null)
                return
            }

            // Overcapacity check — voltage spike blows the bulb.
            if (signal.v > panel.maxVolts) {
                panel.blown      = true
                panel.state      = 'blown'
                panel.brightness = 0
                // Emit the unclamped signal downstream (excess cascades).
                this._emitPower(panel, signal)
                return
            }

            const drawAmps   = panel.watts / NOMINAL_VOLTS
            const voltRatio  = signal.v  / NOMINAL_VOLTS
            const ampRatio   = signal.a  / drawAmps

            if (signal.v < 180 || signal.a < drawAmps * 0.05) {
                panel.state = 'off'; panel.brightness = 0
                this._emitPower(panel, null)
            } else if (voltRatio < 0.9 || ampRatio < 1) {
                panel.state      = 'dim'
                panel.brightness = Math.min(1, voltRatio * Math.min(1, ampRatio)) * 0.55
                this._emitPower(panel, null)
            } else {
                panel.state      = 'on'
                panel.brightness = Math.min(1.0, voltRatio)
                this._emitPower(panel, null)
            }
        },

        _applyLoad(panel, signal) {
            // Once blown, ignore all signals until manually reset.
            if (panel.blown) return

            const drawAmps = panel.watts / NOMINAL_VOLTS

            // Overcapacity: voltage exceeds rated maximum.
            if (signal && signal.v > panel.maxVolts) {
                panel.blown = true
                panel.state = 'blown'
                // Emit the full signal downstream — excess propagates.
                this._emitPower(panel, signal)
                return
            }

            const powered = signal && signal.v >= panel.minVolts && signal.a >= drawAmps

            if (powered) {
                panel._lastGoodSignal = signal
                panel.state = 'on'
                this._emitPower(panel, { v: signal.v, a: signal.a - drawAmps })
            } else if (!signal || signal.v <= 0) {
                // Fully dead — try capacitor
                if (panel.capacitance > 0 && panel.chargeWs > 0) {
                    panel.state = 'capacitor'
                    // Tick handles drain; emit a held signal based on last good
                    const held = panel._lastGoodSignal
                    if (held) this._emitPower(panel, { v: held.v, a: held.a - drawAmps })
                } else {
                    panel.state = 'off'
                    this._emitPower(panel, null)
                }
            } else {
                // Brownout: voltage or amps insufficient but not zero
                panel.state = 'brownout'
                this._emitPower(panel, null)
            }
        },

        _applyMeter(panel, signal) {
            if (!signal || signal.v <= 0) {
                panel.state = 'off'
                panel.volts = 0; panel.amps = 0; panel.watts = 0
                this._emitPower(panel, null)
                return
            }
            panel.state = 'on'
            panel.volts = +signal.v.toFixed(1)
            panel.amps  = +signal.a.toFixed(2)
            panel.watts = +(signal.v * signal.a).toFixed(0)
            this._emitPower(panel, signal)  // pass through unchanged
        },

        /* ── capacitor tick (rAF) ───────────────────────────────────── */

        _startTick() {
            const tick = (ts) => {
                this._tickId = requestAnimationFrame(tick)
                if (!_lastTick) { _lastTick = ts; return }
                const dt = Math.min((ts - _lastTick) / 1000, 0.1)
                _lastTick = ts

                if (!this.graphRunning) return

                this.panels.forEach(p => {
                    if (p.type !== 'load' || p.capacitance <= 0) return

                    if (p.state === 'on') {
                        // Charge up while powered
                        p.chargeWs = Math.min(p.capacitance, p.chargeWs + p.watts * dt)
                    } else if (p.state === 'capacitor') {
                        // Drain stored charge
                        p.chargeWs -= p.watts * dt
                        if (p.chargeWs <= 0) {
                            p.chargeWs = 0
                            p.state    = 'off'
                            this._emitPower(p, null)
                        }
                    }
                })
            }
            this._tickId = requestAnimationFrame(tick)
        },

        /* ── routing ────────────────────────────────────────────────── */

        _getOutboundConns(panel, pipIndex) {
            if (typeof pipesWalker === 'undefined') return []
            const result = []
            const allConns = pipesWalker.connections
            pipesWalker.getConnections(String(panel.id)).forEach(conn => {
                const { sender, receiver } = conn.obj
                let outLabel = sender.label, inLabel  = receiver.label
                let outPip   = sender.pipIndex ?? 0, inPip = receiver.pipIndex ?? 0
                if (sender.direction === 'inbound') {
                    outLabel = receiver.label; inLabel = sender.label
                    outPip   = receiver.pipIndex ?? 0; inPip = sender.pipIndex ?? 0
                }
                if (String(outLabel) !== String(panel.id)) return
                if (outPip !== pipIndex) return
                // Derive the canonical connection key from the raw connections store
                const connKey = Object.keys(allConns).find(k => allConns[k] === conn) || null
                result.push({ inLabel, inPip, connKey })
            })
            return result
        },

        _emitPower(panel, signal) {
            if (typeof pipesWalker === 'undefined') return
            const sourceId = String(panel.id)
            this._getOutboundConns(panel, 0).forEach(({ inLabel, inPip, connKey }) => {
                const target = this.panels.find(p => String(p.id) === String(inLabel))
                if (target) {
                    const transformed = EdgeStore.applyEdge(signal, connKey)
                    this.receive(target, transformed, sourceId)
                }
            })
        },

        // Re-broadcast from all live generators — called after any connection change.
        _repropagateAll() {
            this.panels.forEach(p => {
                if (p.type === 'gen' && p.live) {
                    this._emitPower(p, { v: p.volts, a: p.amps })
                }
            })
            this._updateAllGenDraws()
        },

        /*
          _computeGenDraw — BFS from a gen's outbound pip; sums the share of
          watts this generator is responsible for at each active consuming node.

          Overload thresholds (proportion of rated amps):
            ≤ 1.0   — nominal — emit full rated signal
            1.0–1.3 — overload sag — emit voltage-sagged signal (v × 0.85)
            > 1.3   — hard overload — generator trips, emits null
        */
        _computeGenDraw(gen) {
            const visited = new Set()
            const queue   = [String(gen.id)]
            let totalW    = 0

            while (queue.length) {
                const nodeId = queue.shift()
                if (visited.has(nodeId)) continue
                visited.add(nodeId)

                const p = this.panels.find(p => String(p.id) === nodeId)
                if (!p) continue

                const shareCount = Math.max(1, Object.keys(p.powerSources || {}).length)

                if (p.type === 'bulb' && (p.state === 'on' || p.state === 'dim')) {
                    totalW += p.watts / shareCount
                }
                if (p.type === 'load' && (p.state === 'on' || p.state === 'capacitor')) {
                    totalW += p.watts / shareCount
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
                // Hard trip — cut power
                if (gen.state !== 'tripped') {
                    gen.overload = true
                    gen.state    = 'tripped'
                    this._emitPower(gen, null)
                }
            } else if (ratio > 1.0) {
                // Voltage sag — emit reduced voltage
                const sagVolts = +(gen.volts * 0.85).toFixed(1)
                gen.overload   = true
                gen.state      = 'sag'
                this._emitPower(gen, { v: sagVolts, a: gen.amps })
            } else {
                // Nominal — restore full signal if we were previously sagging
                if (gen.overload) {
                    gen.overload = false
                    gen.state    = 'on'
                    this._emitPower(gen, { v: gen.volts, a: gen.amps })
                } else {
                    gen.state = 'on'
                }
            }
        },

        _updateAllGenDraws() {
            this.panels.forEach(p => { if (p.type === 'gen') this._computeGenDraw(p) })
        },

        /* ── pip drag-and-drop ──────────────────────────────────────── */

        pipStartDrag(event, direction, pip) {
            event.target.classList.add('dragging')
            event.dataTransfer.clearData()
            event.dataTransfer.setData('text/plain', JSON.stringify({
                label: pip.label, direction, pipIndex: pip.index
            }))
        },

        pipEndDrag(event) {
            event.target.classList.remove('dragging')
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        },

        pipOverDrag(event) { event.preventDefault() },

        pipDrop(event, direction, pip) {
            const sender   = JSON.parse(event.dataTransfer.getData('text/plain'))
            const receiver = { label: pip.label, direction, pipIndex: pip.index }
            this.connect(sender, receiver)
        },

        connect(sender, receiver) {
            const connKey = `${sender.label}-${sender.pipIndex ?? 0}-${receiver.label}-${receiver.pipIndex ?? 0}`
            document.dispatchEvent(new CustomEvent('connectnodes', {
                detail: { sender, receiver, line: { color: '#00ff88', width: 2 } }
            }))
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
            // Register edge properties and measure pip-to-pip distance after DOM settles.
            nextTick(() => {
                const conn = pipesWalker?.connections?.[connKey]
                if (conn) EdgeStore.register(connKey, conn.obj)
                this._repropagateAll()
            })
        },

        // Update one or more properties of an edge and immediately repropagate it.
        updateEdge(key, props) {
            EdgeStore.update(key, props)
            this.repropagateEdge(key)
            // Refresh canvas line colour to reflect enabled/disabled state
            if (typeof clItems !== 'undefined' && typeof dispatchRequestDrawEvent !== 'undefined') {
                const conn = pipesWalker?.connections?.[key]
                if (conn) {
                    const edge = EdgeStore.get(key)
                    conn.obj.line = conn.obj.line || {}
                    conn.obj.line.color = edge?.enabled === false ? '#ff333366' : '#00ff88'
                    conn.obj.line.width = edge?.enabled === false ? 1 : 2
                    clItems.layers.forEach(layer => {
                        if (layer.lines?.[key]) {
                            layer.lines[key].lineColor = conn.obj.line.color
                        }
                    })
                }
                dispatchRequestDrawEvent()
            }
        },

        // Push a fresh signal through a single edge identified by its connection key.
        // Useful when edge properties change (resistance, enable/disable).
        repropagateEdge(key) {
            const conn = pipesWalker?.connections?.[key]
            if (!conn) return
            const obj = conn.obj
            // Identify sender panel (the outbound end)
            const isReceiverInbound = obj.receiver?.direction === 'inbound'
            const senderDescriptor   = isReceiverInbound ? obj.sender   : obj.receiver
            const receiverDescriptor = isReceiverInbound ? obj.receiver : obj.sender
            const senderPanel   = this.panels.find(p => String(p.id) === String(senderDescriptor?.label))
            const receiverPanel = this.panels.find(p => String(p.id) === String(receiverDescriptor?.label))
            if (!senderPanel || !receiverPanel) return

            // Determine the outgoing signal from the sender:
            // - Generators produce their own rated signal when live
            // - All other nodes forward their combined inbound signal
            let rawSignal
            if (senderPanel.type === 'gen') {
                rawSignal = (senderPanel.live && senderPanel.state !== 'tripped')
                    ? { v: senderPanel.volts, a: senderPanel.amps }
                    : null
            } else {
                rawSignal = this._combineSources(senderPanel.powerSources ?? {})
            }

            const transformed = EdgeStore.applyEdge(rawSignal, key)
            this.receive(receiverPanel, transformed, String(senderPanel.id))
        },

        // Two-step edge inspector: first click picks a pip, second click opens
        // the edge editor for the wire between those two pips.
        selectEdgePip(pip, direction) {
            if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return

            if (!this.edgeFirst) {
                const hasConn = Object.values(pipesWalker.connections).some(c => {
                    const s = c.obj?.sender
                    const r = c.obj?.receiver
                    return (String(s?.label) === String(pip.label) && s?.pipIndex === pip.index)
                        || (String(r?.label) === String(pip.label) && r?.pipIndex === pip.index)
                })
                if (!hasConn) return
                this.edgeFirst = { pip, direction }
                return
            }

            const first = this.edgeFirst
            this.edgeFirst = null

            if (String(first.pip.label) === String(pip.label) && first.pip.index === pip.index) return

            const aLabel = String(first.pip.label), aIdx = first.pip.index
            const bLabel = String(pip.label),        bIdx = pip.index
            const conns  = pipesWalker.connections

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

            if (!key) return  // no direct wire between these two
            this.activeEdge = { key, edge: EdgeStore.getOrCreate(key) }
            this.edgeMode   = false  // exit selection mode — editor is now open
        },
        // connected pip removes only the wire between those two specific pips.
        disconnectPip(pip, direction) {
            if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return

            // ── Step 1: no pip selected yet — select this one ────────────
            if (!this.disconnectFirst) {
                // Check it actually has at least one connection before selecting
                const hasConn = Object.values(pipesWalker.connections).some(c => {
                    const s = c.obj?.sender
                    const r = c.obj?.receiver
                    return (String(s?.label) === String(pip.label) && s?.pipIndex === pip.index)
                        || (String(r?.label) === String(pip.label) && r?.pipIndex === pip.index)
                })
                if (!hasConn) return   // nothing wired here, ignore click
                this.disconnectFirst = { pip, direction }
                return
            }

            // ── Step 2: second pip clicked ───────────────────────────────
            const first  = this.disconnectFirst
            this.disconnectFirst = null

            // Allow clicking the same pip twice to cancel the selection
            if (String(first.pip.label) === String(pip.label) && first.pip.index === pip.index) return

            const conns = pipesWalker.connections
            const aLabel = String(first.pip.label)
            const aIdx   = first.pip.index
            const bLabel = String(pip.label)
            const bIdx   = pip.index

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

            if (toRemove.length === 0) return   // no direct connection between these two pips

            toRemove.forEach(key => {
                const obj = conns[key].obj
                delete conns[key]
                if (typeof clItems !== 'undefined') {
                    clItems.layers.forEach(layer => { delete layer.lines[key] })
                }

                // Deliver null to the receiver for this specific source so the
                // node re-evaluates its combined signal and cascades downstream.
                // The receiver is whichever end has direction 'inbound'.
                const receiverDescriptor = obj?.receiver?.direction === 'inbound'
                    ? obj.receiver
                    : obj?.sender?.direction  === 'inbound' ? obj.sender : null
                const senderDescriptor   = receiverDescriptor === obj?.receiver ? obj?.sender : obj?.receiver

                if (receiverDescriptor && senderDescriptor) {
                    const receiverPanel = this.panels.find(
                        p => String(p.id) === String(receiverDescriptor.label)
                    )
                    if (receiverPanel) {
                        this.receive(receiverPanel, null, String(senderDescriptor.label))
                    }
                }
            })

            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        },

        /* ── helpers ────────────────────────────────────────────────── */

        chargePercent(panel) {
            if (panel.capacitance <= 0) return 0
            return Math.min(100, (panel.chargeWs / panel.capacitance) * 100)
        },

        /* ── save / restore ─────────────────────────────────────────── */

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
    },

}).mount('#app')
