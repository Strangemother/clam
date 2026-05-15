/*
  prompt-sync.js
  ─────────────────────────────────────────────────────────────────────────────
  Sync node — buffers inbound messages and drains them as a batch.

  Auto-drain triggers:
    - buffer length reaches countWatermark (0 disables)
    - no new message arrives for delayMs milliseconds (0 disables)

  Manual controls:
    - Drain: emit the buffered batch now
    - Empty: clear the buffer without emitting
*/

const SyncMethods = {

    _coerceSyncText(value) {
        if (value == null) return ''
        if (typeof value === 'string') return value
        if (typeof value === 'object') {
            try {
                return JSON.stringify(value)
            } catch (e) {
                return String(value)
            }
        }
        return String(value)
    },

    _normalizeSyncTexts(value) {
        if (Array.isArray(value)) {
            return value.flatMap(item => this._normalizeSyncTexts(item))
        }
        if (value == null) return []
        return [this._coerceSyncText(value)]
    },

    _setSyncState(panel) {
        panel.state = panel.buffer.length ? 'active' : 'idle'
    },

    _clearSyncTimer(panel) {
        if (panel._timerId) {
            clearTimeout(panel._timerId)
            panel._timerId = null
        }
    },

    _armSyncTimer(panel) {
        const delayMs = Number(panel.delayMs) || 0

        this._clearSyncTimer(panel)
        if (!panel.buffer.length || delayMs <= 0) return

        panel._timerId = setTimeout(() => {
            panel._timerId = null
            this.drainSync(panel)
        }, delayMs)
    },

    _buildSyncSignal(panel, entries) {
        const texts = entries.map(entry => entry.content)

        return {
            text: panel.emitList ? texts : texts.join('\n\n'),
            meta: {
                sync: true,
                batchSize: texts.length,
                emitList: Boolean(panel.emitList),
                inputs: entries.map(entry => entry.pipName),
                items: entries.map(entry => ({
                    pipName: entry.pipName,
                    content: entry.content,
                })),
            },
        }
    },

    _receiveSync(panel, signal, inPipIndex) {
        if (signal === null) return

        const pip = panel.pipsInbound.find(candidate => candidate.index === inPipIndex)
        const pipName = pip?.name ?? String(inPipIndex ?? 0)
        const texts = this._normalizeSyncTexts(signal?.text)

        if (!texts.length) return

        texts.forEach(content => {
            panel.buffer.push({
                role: signal?.meta?.role || 'in',
                content,
                pipIndex: inPipIndex,
                pipName,
                receivedAt: Date.now(),
            })
        })

        this._setSyncState(panel)

        const countWatermark = Number(panel.countWatermark) || 0
        if (countWatermark > 0 && panel.buffer.length >= countWatermark) {
            this.drainSync(panel)
            return
        }

        this._armSyncTimer(panel)
    },

    addSyncInboundPip(panel) {
        const nextIndex = panel.pipsInbound.length
            ? Math.max(...panel.pipsInbound.map(pip => pip.index)) + 1
            : 0
        panel.pipsInbound.push({ label: panel.id, index: nextIndex, name: `in${nextIndex}` })
    },

    removeSyncInboundPip(panel, pipIndex) {
        if (panel.pipsInbound.length <= 1) return

        panel.pipsInbound = panel.pipsInbound.filter(pip => pip.index !== pipIndex)
        panel.buffer = panel.buffer.filter(entry => entry.pipIndex !== pipIndex)

        if (!panel.buffer.length) {
            this._clearSyncTimer(panel)
        }
        this._setSyncState(panel)
    },

    drainSync(panel) {
        if (!panel.buffer.length) return

        const entries = panel.buffer.splice(0)
        const signal = this._buildSyncSignal(panel, entries)

        this._clearSyncTimer(panel)
        panel.lastOutput = signal
        this._setSyncState(panel)
        this._emitFromNode(panel, signal)
    },

    emptySync(panel) {
        this._clearSyncTimer(panel)
        panel.buffer = []
        this._setSyncState(panel)
    },

    stopSync(panel) {
        this._clearSyncTimer(panel)
    },
}