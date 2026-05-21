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

function createGatePanel(overrides = {}) {
    return makePanel(Object.assign(makeGatePanel(_uid + 1), overrides))
}

function createSwitchPanel(overrides = {}) {
    return makePanel(Object.assign(makeSwitchPanel(), overrides))
}

function createLedPanel(overrides = {}) {
    return makePanel(Object.assign(makeLedPanel(), overrides))
}

function buildFourBitAdderExample() {
    const panels = []
    const switches = []
    const connections = []
    const panelMap = {}
    const stageColors = ['#79c0ff', '#56d364', '#f2cc60', '#ffa657']
    const carryColor = '#ff7b72'
    const x = { inputs: 40, first: 230, second: 430, outputs: 650, carryLed: 850 }
    const yStart = 140
    const rowGap = 260
    // Default inputs render 5 + 3 = 8 so the example shows a non-trivial result immediately.
    const defaultA = 0b0101
    const defaultB = 0b0011

    const bitState = (value, bit) => (((value >> bit) & 1) === 1 ? '1' : '0')

    const addPanel = (key, panel) => {
        panelMap[key] = panel
        panels.push(panel)
        if (panel.type === 'switch') switches.push(panel)
        return panel
    }

    const addConnection = (fromKey, toKey, receiverPip = 0, line = {}) => {
        connections.push({
            sender: {
                label: panelMap[fromKey].id,
                direction: 'outbound',
                pipIndex: 0,
            },
            receiver: {
                label: panelMap[toKey].id,
                direction: 'inbound',
                pipIndex: receiverPip,
            },
            line,
        })
    }

    addPanel('cin', createSwitchPanel({
        title: 'Cin',
        state: '0',
        position: { x: x.inputs, y: 20 },
    }))

    for (let bit = 0; bit < 4; bit += 1) {
        const y = yStart + bit * rowGap
        const stageColor = stageColors[bit % stageColors.length]
        const carrySource = bit === 0 ? 'cin' : `carry${bit}`

        addPanel(`a${bit}`, createSwitchPanel({
            title: `A${bit}`,
            state: bitState(defaultA, bit),
            position: { x: x.inputs, y },
        }))
        addPanel(`b${bit}`, createSwitchPanel({
            title: `B${bit}`,
            state: bitState(defaultB, bit),
            position: { x: x.inputs, y: y + 110 },
        }))
        addPanel(`xor${bit}`, createGatePanel({
            title: `X${bit}`,
            op: 'xor',
            position: { x: x.first, y },
        }))
        addPanel(`and${bit}`, createGatePanel({
            title: `AB${bit}`,
            op: 'and',
            position: { x: x.first, y: y + 110 },
        }))
        addPanel(`sumGate${bit}`, createGatePanel({
            title: `SX${bit}`,
            op: 'xor',
            position: { x: x.second, y },
        }))
        addPanel(`carryAnd${bit}`, createGatePanel({
            title: `CX${bit}`,
            op: 'and',
            position: { x: x.second, y: y + 110 },
        }))
        addPanel(`sum${bit}`, createLedPanel({
            title: `S${bit}`,
            position: { x: x.outputs, y },
        }))
        addPanel(`carry${bit + 1}`, createGatePanel({
            title: `C${bit + 1}`,
            op: 'or',
            position: { x: x.outputs, y: y + 110 },
        }))

        addConnection(`a${bit}`, `xor${bit}`, 0, { color: stageColor, width: 2 })
        addConnection(`b${bit}`, `xor${bit}`, 1, { color: stageColor, width: 2 })
        addConnection(`a${bit}`, `and${bit}`, 0, { color: stageColor, width: 2 })
        addConnection(`b${bit}`, `and${bit}`, 1, { color: stageColor, width: 2 })

        addConnection(`xor${bit}`, `sumGate${bit}`, 0, { color: stageColor, width: 2 })
        addConnection(carrySource, `sumGate${bit}`, 1, { color: carryColor, width: 2 })
        addConnection(`sumGate${bit}`, `sum${bit}`, 0, { color: stageColor, width: 2 })

        addConnection(carrySource, `carryAnd${bit}`, 0, { color: carryColor, width: 2 })
        addConnection(`xor${bit}`, `carryAnd${bit}`, 1, { color: stageColor, width: 2 })
        addConnection(`and${bit}`, `carry${bit + 1}`, 0, { color: stageColor, width: 2 })
        addConnection(`carryAnd${bit}`, `carry${bit + 1}`, 1, { color: carryColor, width: 2 })
    }

    addPanel('cout', createLedPanel({
        title: 'C4',
        position: { x: x.carryLed, y: yStart + rowGap * 3 + 110 },
    }))
    addConnection('carry4', 'cout', 0, { color: carryColor, width: 2 })

    return { panels, connections, switches }
}

dragHost = new DragSolo()

createApp({

    data() {
        return {
            graphRunning: true,
            loadingExample: false,
            panels:       [],
            logicGateOps,   // from logic-nodes.js
            runtimeReadyPromise: null,
        }
    },

    mounted() {
        this.loadFourBitAdder()
    },

    methods: {

        /* ── spawn helpers ──────────────────────────────────────────── */

        _spawn(panel) {
            this.panels.push(panel)
            nextTick(() => {
                const n = this.$refs[`panel-${panel.id}`][0]
                if (!n) return
                stickAll(n)
                if (panel.position) {
                    n.style.left = `${panel.position.x}px`
                    n.style.top = `${panel.position.y}px`
                }
                dragHost.enable(n)
            })
        },

        waitForRuntime() {
            if (pipesWalker) return Promise.resolve()
            if (!this.runtimeReadyPromise) {
                this.runtimeReadyPromise = new Promise(resolve => {
                    document.addEventListener('DOMContentLoaded', () => resolve(), { once: true })
                })
            }
            return this.runtimeReadyPromise
        },

        async loadFourBitAdder() {
            if (this.loadingExample) return
            this.loadingExample = true

            try {
                await this.waitForRuntime()
                this.graphRunning = true
                if (pipesWalker?.clearConnections) pipesWalker.clearConnections()
                this.panels = []
                _uid = 0
                await nextTick()

                const example = buildFourBitAdderExample()
                example.panels.forEach(panel => this._spawn(panel))
                await nextTick()

                example.connections.forEach(conn => {
                    this.connect(conn.sender, conn.receiver, conn.line)
                })

                example.switches.forEach(panel => {
                    this._emit(panel, panel.state, { silent: true })
                })

                if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
            } finally {
                this.loadingExample = false
            }
        },

        addGate() { this._spawn(createGatePanel()) },
        addSwitch() { this._spawn(createSwitchPanel()) },
        addLed()    { this._spawn(createLedPanel()) },

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
        async receive(panel, value, pipIndex = 0, options = {}) {
            const { silent = false } = options
            const bit = logicNodes._bit(logicNodes._bool(value))
            if (!silent) {
                panel.messages.push({ role: 'input', content: `[${pipIndex}] ${bit}` })
            }

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
                if (!silent) {
                    panel.messages.push({ role: 'output', content: output })
                }

            } else if (panel.type === 'switch') {
                panel.state = bit
                output = bit

            } else if (panel.type === 'led') {
                panel.state = bit
                if (!silent) this.scrollToBottom(panel)
                return   // sink — no forwarding
            }

            if (!silent) this.scrollToBottom(panel)
            this._emit(panel, output, options)
        },

        // Forward a value downstream, preserving the receiver's pip index.
        _emit(panel, value, options = {}) {
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
                if (target) this.receive(target, value, inPip, options)
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

        connect(sender, receiver, lineOverrides = {}) {
            const palette = ['#e6194b','#3cb44b','#ffe119','#4363d8',
                             '#f58231','#911eb4','#46f0f0','#f032e6']
            const line = Object.assign({
                color: palette[Math.floor(Math.random() * palette.length)],
                width: 2,
            }, lineOverrides || {})
            document.dispatchEvent(new CustomEvent('connectnodes', {
                detail: { sender, receiver, line }
            }))
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        },
    },

}).mount('#app')
