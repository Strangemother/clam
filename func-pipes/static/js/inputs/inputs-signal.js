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
      receive(panel, signal, sourceId, inPipIndex)
      Accumulates per-source signals on the panel, then applies
      the node's processor so it can update its display state.

      inPipIndex — the receiver pip index on this panel (passed by _emitFromPip).
      Compute nodes use it to map the incoming value to a named pip.
    */
    receive(panel, signal, sourceId = null, inPipIndex = null) {
        // Compute nodes track values by named pip, not by source id.
        if (panel.type === 'compute' && inPipIndex !== null) {
            const pip     = panel.pipsInbound.find(p => p.index === inPipIndex)
            const pipName = pip?.name ?? String(inPipIndex)
            if (signal === null) delete panel.values[pipName]
            else                 panel.values[pipName] = signal.value ?? null
            this._applyCompute(panel, pipName)
            return
        }

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
    // inPip is forwarded to receive so compute nodes can identify which named pip changed.
    _emitFromPip(panel, pipIndex, signal) {
        if (typeof pipesWalker === 'undefined') return
        const sourceId = String(panel.id)
        this._getOutboundConns(panel, pipIndex).forEach(({ inLabel, inPip }) => {
            const target = this.panels.find(p => String(p.id) === String(inLabel))
            if (target) this.receive(target, signal, sourceId, inPip)
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
