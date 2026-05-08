/*
  power-wiring.js
  ─────────────────────────────────────────────────────────────────────────────
  Pip drag-and-drop, connect, edge update/repropagate, disconnect mode,
  edge inspector mode.
*/

const WiringMethods = {

    /* ── pip drag-and-drop ─────────────────────────────────────────────── */

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

    /* ── edge inspector: two-click pip selection ────────────────────── */

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

    /* ── disconnect mode: two-click wire removal ───────────────────── */

    // connected pip removes only the wire between those two specific pips.
    disconnectPip(pip, direction) {
        if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return

        // ── Step 1: no pip selected yet — select this one ───────────
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

        // ── Step 2: second pip clicked ──────────────────────────────
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
}
