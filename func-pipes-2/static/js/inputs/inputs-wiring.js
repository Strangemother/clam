/*
  inputs-wiring.js
  ─────────────────────────────────────────────────────────────────────────────
  Pip drag-and-drop, connect, disconnect mode.
  Mirrors power-wiring.js but without the EdgeStore resistance model.
*/

const WiringMethods = {

    /* ── pip drag-and-drop ─────────────────────────────────────────── */

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
        document.dispatchEvent(new CustomEvent('connectnodes', {
            detail: { sender, receiver, line: { color: '#5588ff', width: 2 } }
        }))
        if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        nextTick(() => this._repropagateAll())
    },

    /* ── disconnect mode: two-click wire removal ───────────────────── */

    disconnectPip(pip, direction) {
        if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return

        if (!this.disconnectFirst) {
            const hasConn = Object.values(pipesWalker.connections).some(c => {
                const s = c.obj?.sender
                const r = c.obj?.receiver
                return (String(s?.label) === String(pip.label) && s?.pipIndex === pip.index)
                    || (String(r?.label) === String(pip.label) && r?.pipIndex === pip.index)
            })
            if (!hasConn) return
            this.disconnectFirst = { pip, direction }
            return
        }

        const first  = this.disconnectFirst
        this.disconnectFirst = null

        if (String(first.pip.label) === String(pip.label) && first.pip.index === pip.index) return

        const conns  = pipesWalker.connections
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

        if (toRemove.length === 0) return

        toRemove.forEach(key => {
            const obj = conns[key].obj
            delete conns[key]
            if (typeof clItems !== 'undefined') {
                clItems.layers.forEach(layer => { delete layer.lines[key] })
            }
            // Deliver null to the receiver
            const receiverDescriptor = obj?.receiver?.direction === 'inbound'
                ? obj.receiver
                : obj?.sender?.direction === 'inbound' ? obj.sender : null
            const senderDescriptor = receiverDescriptor === obj?.receiver ? obj?.sender : obj?.receiver

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
