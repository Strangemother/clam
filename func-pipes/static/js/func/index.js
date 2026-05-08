const { createApp, nextTick } = Vue

/* ── panel factory ──────────────────────────────────────────────────────── */

let _uid = 0

function makePanel(overrides = {}) {
    const id = ++_uid
    return Object.assign({
        id,
        type:         'default',
        title:        `Node ${id}`,
        pipsInbound:  [{ label: id, index: 0 }],
        pipsOutbound: [{ label: id, index: 0 }],
        fn:           '',   // selected ExecNodes method name, '' = passthrough
        input:        '',
        messages:     [],
    }, overrides)
}

/* ── app ────────────────────────────────────────────────────────────────── */

dragHost = new DragSolo()

createApp({

    data() {
        return {
            graphRunning:  true,
            panels:        [],
            execNodeNames,  // from exec-nodes.js
            valueNodeOps,   // from value-node.js
        }
    },

    methods: {

        _spawnPanel(panel) {
            this.panels.push(panel)
            nextTick(() => {
                const n = this.$refs[`panel-${panel.id}`][0]
                stickAll(n)
                dragHost.enable(n)
            })
        },

        addPanel() {
            this._spawnPanel(makePanel())
        },

        addValuePanel() {
            const id = _uid + 1   // peek at next id before makePanel increments it
            this._spawnPanel(makePanel(makeValuePanel(id)))
        },

        removePanel(i) {
            this.panels.splice(i, 1)
        },

        resetPanel(panel) {
            panel.messages = []
            if (panel.type === 'value') panel.stored = ''
        },

        toggleGraph() {
            this.graphRunning = !this.graphRunning
        },

        /* Send typed input downstream (and record it locally) */
        sendMessage(panel) {
            const text = panel.input.trim()
            if (!text) return
            panel.input = ''
            this.forwardText(panel, text, 'user')
        },

        /* Record a message on this panel, optionally transform it, then forward */
        async forwardText(panel, text, role = 'forwarded') {
            panel.messages.push({ role, content: text })

            let output = text

            if (panel.type === 'value') {
                // combine input with stored value, then persist the result
                try {
                    output = String(valueNode[panel.op](text, panel.stored))
                } catch (e) {
                    output = `[error: ${e.message}]`
                }
                panel.stored = output
                panel.messages.push({ role: 'result', content: output })
            } else if (panel.fn && execNodes[panel.fn]) {
                try {
                    output = String(await execNodes[panel.fn](text))
                } catch (e) {
                    output = `[error: ${e.message}]`
                }
                panel.messages.push({ role: 'result', content: output })
            }

            this.scrollToBottom(panel)

            if (this.graphRunning && typeof pipesWalker !== 'undefined') {
                const ids = pipesWalker.getOutgoingIds(String(panel.id))
                ids.forEach(targetId => {
                    const target = this.panels.find(p => String(p.id) === String(targetId))
                    if (target) this.forwardText(target, output, 'forwarded')
                })
            }
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

        /* ── pip drag-and-drop ──────────────────────────────────────────── */

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

        pipOverDrag(event) {
            event.preventDefault()
        },

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
                width: Math.floor(Math.random() * 4) + 2,
            }
            document.dispatchEvent(new CustomEvent('connectnodes', {
                detail: { sender, receiver, line }
            }))
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        },
    },

}).mount('#app')
