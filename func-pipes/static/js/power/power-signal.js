/*
  power-signal.js
  ─────────────────────────────────────────────────────────────────────────────
  Core signal propagation: receive, combine sources, emit, routing, re-propagate.
*/

const SignalMethods = {

    /* ── breaker control ──────────────────────────────────────────────────── */

    toggleBreaker(panel) {
        if (panel.tripped) {
            panel.tripped = false
            panel.closed  = false
        } else {
            panel.closed = !panel.closed
        }
        this._applyBreaker(panel, panel.signal)
        this._updateAllGenDraws()
    },

    /* ── load: live watt/threshold changes ──────────────────────────────── */

    loadParamsChanged(panel) {
        if (panel.signal !== undefined) this._applyLoad(panel, panel.signal)
        this._updateAllGenDraws()
    },

    /* ── core receive ────────────────────────────────────────────────────── */

    /*
      receive(panel, signal, sourceId)
      Accumulates per-source signals, then re-derives a combined signal
      and applies the node's processor.

      Combined from parallel sources:
        v = max voltage across live sources  (dominant rail)
        a = sum of available amps            (parallel capacity)
      When signal is null, that source's contribution is removed.
    */
    receive(panel, signal, sourceId = null) {
        if (sourceId !== null) {
            if (signal === null) {
                delete panel.powerSources[sourceId]
            } else {
                panel.powerSources[sourceId] = signal
            }
        }

        const combined = this._combineSources(panel.powerSources)
        panel.signal   = combined

        if (panel.type === 'breaker') this._applyBreaker(panel, combined)
        if (panel.type === 'bulb')    this._applyBulb(panel, combined)
        if (panel.type === 'load')    this._applyLoad(panel, combined)
        if (panel.type === 'meter')   this._applyMeter(panel, combined)
    },

    /*
      _combineSources — fold all live source signals into one.
      Returns null when no sources remain.
    */
    _combineSources(sources) {
        const live = Object.values(sources).filter(s => s !== null && s.v > 0)
        if (!live.length) return null
        return {
            v: Math.max(...live.map(s => s.v)),
            a: live.reduce((sum, s) => sum + s.a, 0),
        }
    },

    /* ── routing ─────────────────────────────────────────────────────────── */

    _getOutboundConns(panel, pipIndex) {
        if (typeof pipesWalker === 'undefined') return []
        const result = []
        const allConns = pipesWalker.connections
        pipesWalker.getConnections(String(panel.id)).forEach(conn => {
            const { sender, receiver } = conn.obj
            let outLabel = sender.label, inLabel  = receiver.label
            let outPip   = sender.pipIndex ?? 0, inPip = receiver.pipIndex ?? 0
            if (sender.direction === 'inbound') {
                outLabel = receiver.label; inLabel = sender.label
                outPip   = receiver.pipIndex ?? 0; inPip = sender.pipIndex ?? 0
            }
            if (String(outLabel) !== String(panel.id)) return
            if (outPip !== pipIndex) return
            // Derive the canonical connection key from the raw connections store
            const connKey = Object.keys(allConns).find(k => allConns[k] === conn) || null
            result.push({ inLabel, inPip, connKey })
        })
        return result
    },

    _emitPower(panel, signal) {
        if (typeof pipesWalker === 'undefined') return
        const sourceId = String(panel.id)
        this._getOutboundConns(panel, 0).forEach(({ inLabel, inPip, connKey }) => {
            const target = this.panels.find(p => String(p.id) === String(inLabel))
            if (target) {
                const transformed = EdgeStore.applyEdge(signal, connKey)
                this.receive(target, transformed, sourceId)
            }
        })
    },

    // Re-broadcast from all live generators — called after any connection change.
    _repropagateAll() {
        this.panels.forEach(p => {
            if (p.type === 'gen' && p.live) {
                this._emitPower(p, { v: p.volts, a: p.amps })
            }
        })
        this._updateAllGenDraws()
    },
}
