/*
  inputs-signal.js
  ─────────────────────────────────────────────────────────────────────────────
  Core signal propagation for the inputs system.

  Unlike the power system, signals here are { value } payloads — no
  voltage/amp combining.  Each pip is an independent channel; a gamepad
  can emit from multiple pips simultaneously (one per button/axis).

  Routing mirrors power-signal.js — uses the same pipesWalker infrastructure.
*/

const SignalMethods = {

    /* ── receive ────────────────────────────────────────────────────── */

    /*
      receive(panel, signal, sourceId)
      Accumulates per-source signals on the panel, then applies
      the node's processor so it can update its display state.
    */
    receive(panel, signal, sourceId = null) {
        if (sourceId !== null) {
            if (signal === null) delete panel.sources[sourceId]
            else                 panel.sources[sourceId] = signal
        }
        const combined = this._combineSources(panel.sources)
        this._applyNode(panel, combined)
    },

    /*
      _combineSources — for inputs, "first live source wins".
      A value node typically has one upstream connection; if wired to
      multiple outputs, it shows the first non-null value received.
    */
    _combineSources(sources) {
        const live = Object.values(sources).filter(s => s !== null)
        return live.length ? live[0] : null
    },

    /* ── node processor dispatch ─────────────────────────────────────── */

    _applyNode(panel, signal) {
        if (panel.type === 'value') this._applyValue(panel, signal)
    },

    _applyValue(panel, signal) {
        panel.value = signal?.value ?? null
        panel.state = signal !== null ? 'active' : 'idle'
        // Value is currently a sink — no forwarding needed.
        // _emitFromNode is here so value→value chains work if pipsOutbound grow.
        this._emitFromNode(panel, signal)
    },

    /* ── routing ─────────────────────────────────────────────────────── */

    _getOutboundConns(panel, pipIndex) {
        if (typeof pipesWalker === 'undefined') return []
        const result   = []
        const allConns = pipesWalker.connections
        pipesWalker.getConnections(String(panel.id)).forEach(conn => {
            const { sender, receiver } = conn.obj
            let outLabel = sender.label,        inLabel  = receiver.label
            let outPip   = sender.pipIndex ?? 0, inPip   = receiver.pipIndex ?? 0
            if (sender.direction === 'inbound') {
                outLabel = receiver.label; inLabel = sender.label
                outPip   = receiver.pipIndex ?? 0; inPip = sender.pipIndex ?? 0
            }
            if (String(outLabel) !== String(panel.id)) return
            if (outPip !== pipIndex) return
            const connKey = Object.keys(allConns).find(k => allConns[k] === conn) || null
            result.push({ inLabel, inPip, connKey })
        })
        return result
    },

    // Emit a signal from one specific outbound pip (used by gamepad per-button).
    _emitFromPip(panel, pipIndex, signal) {
        if (typeof pipesWalker === 'undefined') return
        const sourceId = String(panel.id)
        this._getOutboundConns(panel, pipIndex).forEach(({ inLabel }) => {
            const target = this.panels.find(p => String(p.id) === String(inLabel))
            if (target) this.receive(target, signal, sourceId)
        })
    },

    // Emit from every outbound pip (for pass-through nodes).
    _emitFromNode(panel, signal) {
        ;(panel.pipsOutbound || []).forEach(pip => {
            this._emitFromPip(panel, pip.index, signal)
        })
    },

    // Re-emit all current gamepad values — called after wiring changes.
    _repropagateAll() {
        this.panels.forEach(p => {
            if (p.type !== 'gamepad') return
            p.pipsOutbound.forEach(pip => {
                const val = p.currentValues[pip.index] ?? null
                const sig = val !== null ? { value: val } : null
                this._emitFromPip(p, pip.index, sig)
            })
        })
    },
}
