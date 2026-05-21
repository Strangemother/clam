/*
  logic-index.js
  ──────────────
  Vue app for the logic-gate page.

  Panel types:
    gate   — logic gate (AND, OR, NOT, …). Receives a value, combines with
             its latched B-input (stored), emits the result downstream.
    switch — manual toggle source. Fires its current state (0/1) downstream
             when the button is clicked, or when it receives a pipe value.
    led    — sink/indicator. Receives a value and lights up; does not forward.
*/

const { createApp, nextTick } = Vue

let _uid = 0

function makePanel(overrides = {}) {
    const id = ++_uid
    return Object.assign({
        id,
        title:        `Node ${id}`,
        pipsInbound:  [{ label: id, index: 0 }],
        pipsOutbound: [{ label: id, index: 0 }],
        input:        '',
        messages:     [],
    }, overrides)
}

dragHost = new DragSolo()

createApp({

    data() {
        return {
            graphRunning: true,
            panels:       [],
            logicGateOps,   // from logic-nodes.js
        }
    },

    methods: {

        /* ── spawn helpers ──────────────────────────────────────────── */

        _spawn(panel) {
            this.panels.push(panel)
            nextTick(() => {
                const n = this.$refs[`panel-${panel.id}`][0]
                stickAll(n)
                dragHost.enable(n)
            })
        },

        addGate() {
            const id = _uid + 1  // peek before makePanel increments
            this._spawn(makePanel(makeGatePanel(id)))
        },
        addSwitch() { this._spawn(makePanel(makeSwitchPanel())) },
        addLed()    { this._spawn(makePanel(makeLedPanel())) },

        removePanel(i) { this.panels.splice(i, 1) },

        resetPanel(panel) {
            panel.messages = []
            if (panel.type === 'gate')   { panel.inputs = ['0', '0']; panel.state = '?' }
            if (panel.type === 'switch') { panel.state = '0' }
            if (panel.type === 'led')    { panel.state = '0' }
        },

        toggleGraph() { this.graphRunning = !this.graphRunning },

        /* ── switch: manual fire ────────────────────────────────────── */

        toggleSwitch(panel) {
            panel.state = panel.state === '1' ? '0' : '1'
            this._emit(panel, panel.state)
        },

        /* ── core forwarding ────────────────────────────────────────── */

        // Receive a value into a panel on a specific pip, process it, forward the result.
        async receive(panel, value, pipIndex = 0) {
            const bit = logicNodes._bit(logicNodes._bool(value))
            panel.messages.push({ role: 'input', content: `[${pipIndex}] ${bit}` })

            let output = bit

            if (panel.type === 'gate') {
                panel.inputs[pipIndex] = bit
                const [a, b] = panel.inputs
                try {
                    output = UNARY_GATES.has(panel.op)
                        ? logicNodes[panel.op](a)
                        : logicNodes[panel.op](a, b)
                    panel.state = output
                } catch (e) {
                    output = '?'
                    panel.state = '?'
                }
                panel.messages.push({ role: 'output', content: output })

            } else if (panel.type === 'switch') {
                panel.state = bit
                output = bit

            } else if (panel.type === 'led') {
                panel.state = bit
                this.scrollToBottom(panel)
                return   // sink — no forwarding
            }

            this.scrollToBottom(panel)
            this._emit(panel, output)
        },

        // Forward a value downstream, preserving the receiver's pip index.
        _emit(panel, value) {
            if (!this.graphRunning || typeof pipesWalker === 'undefined') return
            const conns = pipesWalker.getConnections(String(panel.id))
            conns.forEach(conn => {
                const { sender, receiver } = conn.obj
                // normalise direction: sender is always outbound
                let outLabel = sender.label, inLabel = receiver.label, inPip = receiver.pipIndex ?? 0
                if (sender.direction === 'inbound') {
                    outLabel = receiver.label; inLabel = sender.label; inPip = sender.pipIndex ?? 0
                }
                if (String(outLabel) !== String(panel.id)) return
                const target = this.panels.find(p => String(p.id) === String(inLabel))
                if (target) this.receive(target, value, inPip)
            })
        },

        // Manual text input field — coerce to bit then receive.
        sendMessage(panel) {
            const text = panel.input.trim()
            if (!text) return
            panel.input = ''
            const bit = logicNodes._bit(logicNodes._bool(text))
            this.receive(panel, bit)
        },

        copyMessage(m) {
            navigator.clipboard.writeText(m.content).catch(e => console.error('[Copy]', e))
        },

        scrollToBottom(panel) {
            nextTick(() => {
                const el = this.$refs['msgs-' + panel.id]?.[0]
                if (el) el.scrollTop = el.scrollHeight
            })
        },

        /* ── pip drag-and-drop ──────────────────────────────────────── */

        pipStartDrag(event, direction, pip) {
            event.target.classList.add('dragging')
            event.dataTransfer.clearData()
            event.dataTransfer.setData('text/plain', JSON.stringify({
                label: pip.label, direction, pipIndex: pip.index
            }))
        },

        pipEndDrag(event, direction, pip) {
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
            const palette = ['#e6194b','#3cb44b','#ffe119','#4363d8',
                             '#f58231','#911eb4','#46f0f0','#f032e6']
            const line = {
                color: palette[Math.floor(Math.random() * palette.length)],
                width: 2,
            }
            document.dispatchEvent(new CustomEvent('connectnodes', {
                detail: { sender, receiver, line }
            }))
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        },
    },

}).mount('#app')
