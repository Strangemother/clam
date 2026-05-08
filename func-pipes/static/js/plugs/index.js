/*
  plugs-index.js
  ──────────────
  Vue app for the power plugs page.

  Power values are numeric (watts) rather than binary.
  All nodes share a 2-in / 2-out pip layout:
    pip index 0 = power channel
    pip index 1 = auxiliary channel (passed through unchanged)

  Node receive contract:
    receive(panel, value, pipIndex)
      → battery : passes value through on the same pip (power flows in and out)
      → module  : pip 0 — consumes panel.usage watts, emits remainder on pip 0
                  pip 1 — pass-through
      → meter   : pip 0 — updates reading and peak, then passes through
                  pip 1 — pass-through

  _emit(panel, value, pipIndex) routes value only along connections that
  originate from outbound pip `pipIndex` of this panel.
*/

const { createApp, nextTick } = Vue

let _uid = 0

// Scale reference for the meter bar display (100 % = METER_SCALE watts)
const METER_SCALE = 500

function makePanel(overrides = {}) {
    const id = ++_uid
    return Object.assign({
        id,
        title: `Node ${id}`,
        // Factories always supply their own pip arrays; these are fallback only.
        pipsInbound:  [{ label: id, index: 0 }, { label: id, index: 1 }],
        pipsOutbound: [{ label: id, index: 0 }, { label: id, index: 1 }],
    }, overrides)
}

dragHost = new DragSolo()

createApp({

    data() {
        return {
            graphRunning: true,
            panels: [],
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

        addBattery() { this._spawn(makePanel(makeBatteryPanel(_uid + 1))) },
        addModule()  { this._spawn(makePanel(makeModulePanel(_uid + 1))) },
        addMeter()   { this._spawn(makePanel(makeMeterPanel(_uid + 1))) },

        removePanel(i) { this.panels.splice(i, 1) },

        resetPanel(panel) {
            panel.state = 0
            if (panel.type === 'battery') {
                panel.connectionCount = 0; panel.outputEdges = []
            }
            if (panel.type === 'module') {
                panel.powerIn = 0; panel.powerUsed = 0; panel.powerOut = 0
                panel.powerSources = {}
            }
            if (panel.type === 'meter') {
                panel.peak = 0
                panel.powerSources = {}
            }
        },

        toggleGraph() { this.graphRunning = !this.graphRunning },

        /* ── battery: manual fire ───────────────────────────────────── */

        fireBattery(panel) {
            if (!this.graphRunning) return
            // Count live outbound PWR connections and split watts evenly.
            const outConns = this._getOutboundConns(panel, 0)
            const count    = outConns.length || 1
            const perNode  = panel.watts / count
            panel.state           = panel.watts
            panel.connectionCount = count
            panel.outputEdges     = outConns.map(c => ({
                targetId: c.inLabel,
                watts: +perNode.toFixed(2)
            }))
            this._emit(panel, perNode, 0)
        },

        /* ── core receive / forward ─────────────────────────────────── */

        /*
          receive — called per incoming connection edge.
          sourceId identifies the sending panel so each contribution is
          stored separately; the running sum handles multiple batteries.
        */
        receive(panel, value, pipIndex = 0, sourceId = null) {
            const watts = parseFloat(value) || 0

            if (panel.type === 'battery') {
                panel.state = watts
                this._emit(panel, watts, pipIndex)

            } else if (panel.type === 'module') {
                if (pipIndex === 0) {
                    if (sourceId !== null) panel.powerSources[sourceId] = watts
                    const totalIn   = Object.values(panel.powerSources).reduce((a, b) => a + b, 0)
                    panel.powerIn   = +totalIn.toFixed(2)
                    panel.powerUsed = +Math.min(panel.usage, totalIn).toFixed(2)
                    panel.powerOut  = +Math.max(0, totalIn - panel.usage).toFixed(2)
                    panel.state     = panel.powerOut
                    this._emit(panel, panel.powerOut, 0)
                } else {
                    this._emit(panel, watts, pipIndex)
                }

            } else if (panel.type === 'meter') {
                if (pipIndex === 0) {
                    if (sourceId !== null) panel.powerSources[sourceId] = watts
                    const totalIn = Object.values(panel.powerSources).reduce((a, b) => a + b, 0)
                    panel.state   = +totalIn.toFixed(2)
                    if (totalIn > panel.peak) panel.peak = +totalIn.toFixed(2)
                    this._emit(panel, panel.state, 0)
                } else {
                    this._emit(panel, watts, pipIndex)
                }
            }
        },

        /* _getOutboundConns — returns [{inLabel, inPip}] for a given outbound pip. */
        _getOutboundConns(panel, pipIndex) {
            if (typeof pipesWalker === 'undefined') return []
            const result = []
            pipesWalker.getConnections(String(panel.id)).forEach(conn => {
                const { sender, receiver } = conn.obj
                let outLabel = sender.label, inLabel = receiver.label
                let inPip    = receiver.pipIndex ?? 0, outPip = sender.pipIndex ?? 0
                if (sender.direction === 'inbound') {
                    outLabel = receiver.label; inLabel  = sender.label
                    inPip    = sender.pipIndex ?? 0; outPip = receiver.pipIndex ?? 0
                }
                if (String(outLabel) !== String(panel.id)) return
                if (outPip !== pipIndex) return
                result.push({ inLabel, inPip })
            })
            return result
        },

        /*
          _emit — forward value on a specific outbound pip, passing sourceId
          so receivers can accumulate contributions per sender.
        */
        _emit(panel, value, pipIndex) {
            if (!this.graphRunning || typeof pipesWalker === 'undefined') return
            const sourceId = String(panel.id)
            this._getOutboundConns(panel, pipIndex).forEach(({ inLabel, inPip }) => {
                const target = this.panels.find(p => String(p.id) === String(inLabel))
                if (target) this.receive(target, value, inPip, sourceId)
            })
        },

        /* ── meter bar percent ──────────────────────────────────────── */

        meterPercent(panel) {
            return Math.min(100, (panel.state / METER_SCALE) * 100)
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
            const palette = ['#ffd166','#f5a623','#f78166','#e63946',
                             '#a8dadc','#56d364','#4363d8']
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
