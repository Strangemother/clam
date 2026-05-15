/*
  prompt-wait.js
  ─────────────────────────────────────────────────────────────────────────────
  Wait node — emits a timeout message after a period of inactivity.

    Behavior:
        - inbound message arrives on pip 'in' → forward immediately on outbound
            pip 'out' and reset the inactivity timer
        - any signal arrives on pip 'reset' → reset the inactivity timer without
            forwarding a message downstream
    - no inbound message arrives before delayMs elapses → emit waitMessage
      on outbound pip 'waiting'
*/

const WaitMethods = {

    _coerceWaitPreview(value) {
        if (Array.isArray(value)) {
            return value.map(item => this._coerceWaitPreview(item)).filter(Boolean).join(' | ')
        }
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

    _formatWaitDelay(delayMs) {
        const ms = Math.max(0, Number(delayMs) || 0)
        if (ms === 0) return '0 ms'
        if (ms % 60000 === 0) {
            const minutes = ms / 60000
            return `${minutes} minute${minutes === 1 ? '' : 's'}`
        }
        if (ms % 1000 === 0) {
            const seconds = ms / 1000
            return `${seconds} second${seconds === 1 ? '' : 's'}`
        }
        return `${ms} ms`
    },

    _defaultWaitMessage(panel) {
        return `No message received for ${this._formatWaitDelay(panel.delayMs)}`
    },

    _clearWaitTimer(panel) {
        if (panel._timerId) {
            clearTimeout(panel._timerId)
            panel._timerId = null
        }
    },

    armWaitTimer(panel) {
        const delayMs = Number(panel.delayMs) || 0

        this._clearWaitTimer(panel)

        if (delayMs <= 0) {
            panel.state = 'idle'
            return
        }

        panel.state = 'waiting'
        panel._timerId = setTimeout(() => {
            panel._timerId = null
            this._emitWaitTimeout(panel)
        }, delayMs)
    },

    refreshWaitTimer(panel) {
        this.armWaitTimer(panel)
    },

    _emitWaitTimeout(panel) {
        const text = String(panel.waitMessage || '').trim() || this._defaultWaitMessage(panel)
        const signal = {
            text,
            meta: {
                role: 'status',
                wait: true,
                timeoutMs: Number(panel.delayMs) || 0,
            },
        }

        panel.lastTimeoutText = text
        panel.lastTimeoutAt = new Date().toLocaleTimeString()
        panel.state = 'timeout'
        panel.lastOutputByPip[1] = signal

        this._emitFromPip(panel, 1, signal)
    },

    _receiveWait(panel, signal, inPipIndex = 0) {
        if (signal === null) return

        const pip = panel.pipsInbound.find(candidate => candidate.index === inPipIndex)
        const pipName = pip?.name ?? String(inPipIndex)

        this._clearWaitTimer(panel)

        if (pipName === 'reset') {
            panel.lastOutputByPip[1] = null
            this._emitFromPip(panel, 1, null)
            this.armWaitTimer(panel)
            return
        }

        panel.lastReceivedText = this._coerceWaitPreview(signal?.text)
        panel.lastReceivedAt = new Date().toLocaleTimeString()
        panel.lastOutputByPip[0] = signal
        panel.lastOutputByPip[1] = null

        this._emitFromPip(panel, 1, null)
        this._emitFromPip(panel, 0, signal)
        this.armWaitTimer(panel)
    },

    stopWait(panel) {
        this._clearWaitTimer(panel)
    },
}