/*
  prompt-event.js
  ─────────────────────────────────────────────────────────────────────────────
  Event Input node — listens for a named DOM CustomEvent on window and routes
  its detail to outbound pips.

  Event shape accepted:

    // scalar — emits as { text } on the first outbound pip
    window.dispatchEvent(new CustomEvent('graph:input', { detail: 'hello' }))

    // keyed object — routes each key to the matching pip by name
    window.dispatchEvent(new CustomEvent('graph:input', {
      detail: { out: 'hello', count: 42 }
    }))

  The event name is configurable per node.
  Pips can be added or removed; their names define which detail keys they accept.

  Usage from another process / WebSocket:
    Receive a message, then:
      window.dispatchEvent(new CustomEvent('graph:input', { detail: parsed }))
    That's it — all connected Event Input nodes listening on that name will fire.
*/

const EventMethods = {

    /* ── listener lifecycle ─────────────────────────────────────────── */

    mountEventInput(panel) {
        if (panel._listener) return  // already mounted
        panel._listener = (e) => this._applyEventInput(panel, e.detail)
        window.addEventListener(panel.eventName, panel._listener)
    },

    unmountEventInput(panel) {
        if (!panel._listener) return
        window.removeEventListener(panel.eventName, panel._listener)
        panel._listener = null
    },

    // Call when the event name changes
    remountEventInput(panel) {
        this.unmountEventInput(panel)
        this.mountEventInput(panel)
    },

    /* ── signal dispatch ────────────────────────────────────────────── */

    _applyEventInput(panel, detail) {
        panel.lastReceived = new Date().toLocaleTimeString()
        panel.lastDetail   = typeof detail === 'object' && detail !== null
            ? JSON.stringify(detail)
            : String(detail ?? '')
        panel.state = 'active'
        clearTimeout(panel._stateTimer)
        panel._stateTimer = setTimeout(() => { panel.state = 'idle' }, 600)

        if (detail === null || detail === undefined) {
            // null detail → clear all outbound
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
            return
        }

        if (typeof detail === 'object' && !Array.isArray(detail)) {
            // Object — route each key to the matching pip by name
            panel.pipsOutbound.forEach(pip => {
                if (Object.prototype.hasOwnProperty.call(detail, pip.name)) {
                    const val = detail[pip.name]
                    const text = typeof val === 'string' ? val : JSON.stringify(val)
                    this._emitFromPip(panel, pip.index, { text, meta: { event: panel.eventName } })
                }
            })
        } else {
            // Scalar — emit on the first pip only
            if (panel.pipsOutbound.length) {
                const text = typeof detail === 'string' ? detail : JSON.stringify(detail)
                this._emitFromPip(panel, panel.pipsOutbound[0].index,
                    { text, meta: { event: panel.eventName } })
            }
        }
    },

    /* ── outbound pip management ────────────────────────────────────── */

    addEventOutboundPip(panel) {
        const nextIndex = panel.pipsOutbound.length
            ? Math.max(...panel.pipsOutbound.map(p => p.index)) + 1
            : 0
        panel.pipsOutbound.push({ label: panel.id, index: nextIndex, name: `pip${nextIndex}` })
    },

    removeEventOutboundPip(panel, index) {
        const i = panel.pipsOutbound.findIndex(p => p.index === index)
        if (i === -1) return
        this._emitFromPip(panel, index, null)
        panel.pipsOutbound.splice(i, 1)
    },

    /* ── test helper ────────────────────────────────────────────────── */

    // Fires a test event on the current node's eventName.
    // Called from the panel's "Test" button.
    dispatchTestEvent(panel) {
        const detail = {}
        panel.pipsOutbound.forEach(pip => { detail[pip.name] = `test:${pip.name}` })
        window.dispatchEvent(new CustomEvent(panel.eventName, {
            detail: panel.pipsOutbound.length === 1 ? `test:${panel.pipsOutbound[0].name}` : detail
        }))
    },
}
