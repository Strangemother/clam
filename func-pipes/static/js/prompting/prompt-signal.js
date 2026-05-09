/*
  prompt-signal.js
  ─────────────────────────────────────────────────────────────────────────────
  Core signal propagation for the prompting system.

  Signal format:  { text: string, meta?: {} }  |  null

  Routing mirrors inputs-signal.js — named pips identify the channel, and
  each node type has its own processor dispatch.

  Unlike the numeric inputs system, signals carry arbitrary text/objects.
  Combining strategy: first-live-wins (same as inputs) — not summed.
*/

const SignalMethods = {

    /* ── receive ────────────────────────────────────────────────────── */

    /*
      receive(panel, signal, sourceId, inPipIndex)

      inPipIndex — the receiver pip index on this panel (forwarded by
                   _emitFromPip so named-pip nodes can identify which
                   channel changed).

      transform and llm nodes route by named pip; other nodes use
      _combineSources first-wins logic.
    */
    receive(panel, signal, sourceId = null, inPipIndex = null) {

        // Transform: track values per named pip, apply fn on change
        if (panel.type === 'transform' && inPipIndex !== null) {
            const pip     = panel.pipsInbound.find(p => p.index === inPipIndex)
            const pipName = pip?.name ?? String(inPipIndex)
            if (signal === null) delete panel.values[pipName]
            else                 panel.values[pipName] = signal.text ?? ''
            this._applyTransform(panel, pipName)
            return
        }

        // LLM: route 'in' pip → send to model; 'system' pip → update system prompt
        if (panel.type === 'llm' && inPipIndex !== null) {
            const pip     = panel.pipsInbound.find(p => p.index === inPipIndex)
            const pipName = pip?.name ?? String(inPipIndex)
            if (pipName === 'system') {
                // Store the override; _getLLMChat will apply it on the next send
                panel._systemOverride = signal?.text ?? ''
                if (panel._chat) panel._chat.options.system = panel._systemOverride
                else              panel._pendingSystem = panel._systemOverride
            } else {
                // 'in' or any unnamed inbound — treat as a message to send
                if (signal !== null) this._applyLLM(panel, signal.text ?? '', signal.meta)
            }
            return
        }

        // text-input in pass-through mode: forward downstream unchanged
        if (panel.type === 'text-input') {
            if (signal !== null) {
                panel.messages.push({ role: 'relay', text: signal.text ?? '' })
                panel.lastOutput = signal
                this._emitFromNode(panel, signal)
            } else {
                panel.lastOutput = null
                this._emitFromNode(panel, null)
            }
            return
        }

        // text-display: combine sources, update display
        if (sourceId !== null) {
            if (signal === null) delete panel.sources[sourceId]
            else                 panel.sources[sourceId] = signal
        }
        const combined = this._combineSources(panel.sources)
        this._applyNode(panel, combined)
    },

    /*
      _combineSources — first live source wins.
      Prompting signals aren't additive; the first non-null signal is used.
    */
    _combineSources(sources) {
        const live = Object.values(sources).filter(s => s !== null)
        return live.length ? live[0] : null
    },

    /* ── node processor dispatch ─────────────────────────────────────── */

    _applyNode(panel, signal) {
        if (panel.type === 'text-display') this._applyTextDisplay(panel, signal)
    },

    _applyTextDisplay(panel, signal) {
        panel.state = signal !== null ? 'active' : 'idle'
        if (signal !== null) {
            panel.messages.push({ role: signal.meta?.role || 'in', text: signal.text ?? '' })
        }
        // Pass signal downstream so display nodes can be chained
        this._emitFromNode(panel, signal)
    },

    /* ── routing ─────────────────────────────────────────────────────── */

    _getOutboundConns(panel, pipIndex) {
        if (typeof pipesWalker === 'undefined') return []
        const result   = []
        const allConns = pipesWalker.connections
        pipesWalker.getConnections(String(panel.id)).forEach(conn => {
            const { sender, receiver } = conn.obj
            let outLabel = sender.label,          inLabel  = receiver.label
            let outPip   = sender.pipIndex ?? 0,  inPip    = receiver.pipIndex ?? 0
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

    // Emit a signal from one specific outbound pip.
    // inPip is forwarded to receive() so named-pip nodes can identify the channel.
    _emitFromPip(panel, pipIndex, signal) {
        if (typeof pipesWalker === 'undefined') return
        const sourceId = String(panel.id)
        this._getOutboundConns(panel, pipIndex).forEach(({ inLabel, inPip }) => {
            const target = this.panels.find(p => String(p.id) === String(inLabel))
            if (target) this.receive(target, signal, sourceId, inPip)
        })
    },

    // Emit from every outbound pip (pass-through nodes).
    _emitFromNode(panel, signal) {
        ;(panel.pipsOutbound || []).forEach(pip => {
            this._emitFromPip(panel, pip.index, signal)
        })
    },

    // Re-emit last known output on all outbound pips — called after wiring changes.
    _repropagateAll() {
        this.panels.forEach(p => {
            if (p.lastOutput !== undefined) {
                p.pipsOutbound?.forEach(pip => {
                    const sig = p.lastOutput ?? null
                    this._emitFromPip(p, pip.index, sig)
                })
            }
            // Transform: re-run fn with whatever values are known
            if (p.type === 'transform') {
                const pip = p.pipsInbound.find(pip => p.values[pip.name] !== undefined)
                if (pip) this._applyTransform(p, pip.name)
            }
        })
    },
}
