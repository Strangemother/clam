/*
  prompt-grad-voice-result.js
  ─────────────────────────────────────────────────────────────────────────────
  Grad Voice Result node — waits for a previously created Grad Voice event to
  complete, resolves any generated FileData outputs via the Flask backend, and
  emits the first proxied audio URL downstream.
*/

const GradVoiceResultMethods = {

    _scrollGradVoiceResultMessages(panel) {
        nextTick(() => {
            const ref = this.$refs[`msgs-${panel.id}`]
            const el = Array.isArray(ref) ? ref[0] : ref
            if (!el) return
            el.scrollTop = el.scrollHeight
        })
    },

    _getGradVoiceResultAudio(panel) {
        const ref = this.$refs[`audio-${panel.id}`]
        return Array.isArray(ref) ? ref[0] : ref
    },

    _extractGradVoiceEventId(text, meta = {}) {
        const candidates = [meta?.event_id, text]

        for (const candidate of candidates) {
            if (candidate == null) continue
            const raw = String(candidate).trim()
            if (!raw) continue

            try {
                const parsed = JSON.parse(raw)
                const nested = String(parsed?.event_id || '').trim()
                if (nested) return nested
            } catch (e) {
                // plain text event ids are expected; ignore parse failures
            }

            return raw
        }

        return ''
    },

    async _applyGradVoiceResult(panel, text, meta = {}) {
        const eventId = this._extractGradVoiceEventId(text, meta)
        if (!eventId) return

        if (panel._controller) panel._controller.abort()
        panel._controller = new AbortController()

        panel.lastEventId = eventId
        panel.lastError = null
        panel.messages.push({ role: meta?.role || 'user', content: eventId })
        panel.state = 'pending'
        this._scrollGradVoiceResultMessages(panel)

        try {
            const res = await fetch(`${PROMPTING_API_BASE}/grad-voice/result/`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ event_id: eventId }),
                signal:  panel._controller.signal,
            })
            const data = await res.json().catch(() => ({}))

            if (!res.ok) {
                const detail = data.error
                    || data.message
                    || `request failed (${res.status})`
                throw Object.assign(new Error(String(detail)), { data })
            }

            const files = Array.isArray(data.files) ? data.files : []
            const audioUrl = String(data.first_file_url || files[0]?.proxy_url || '').trim()
            const outputText = audioUrl || JSON.stringify(data.payloads ?? data)

            panel.lastResponse = data
            panel.lastFiles = files
            panel.audioUrl = audioUrl
            panel.messages.push({ role: 'assistant', content: outputText })
            panel.state = 'idle'

            const sig = {
                text: outputText,
                meta: {
                    role: 'assistant',
                    service: 'grad-voice-result',
                    event_id: eventId,
                    files,
                    response: data,
                },
            }
            panel.lastOutput = sig
            this._scrollGradVoiceResultMessages(panel)
            this._emitFromNode(panel, sig)

            if (panel.autoPlay && panel.audioUrl) {
                await this.playGradVoiceResult(panel)
            }

        } catch (e) {
            if (e?.name !== 'AbortError') {
                panel.lastError = e.message
                panel.messages.push({ role: 'error', content: `Error: ${e.message}` })
                panel.state = 'error'
                this._scrollGradVoiceResultMessages(panel)
                console.error('[GradVoiceResult error]', e.message, e.data ?? '')
            } else {
                panel.state = 'idle'
            }
        } finally {
            panel._controller = null
        }
    },

    async playGradVoiceResult(panel) {
        if (!panel.audioUrl) return

        await nextTick()

        const el = this._getGradVoiceResultAudio(panel)
        if (!el) return

        try {
            el.currentTime = 0
            await el.play()
        } catch (e) {
            panel.lastError = `play failed: ${e.message}`
            console.warn('[GradVoiceResult play]', e)
        }
    },

    stopGradVoiceResult(panel) {
        if (panel._controller) panel._controller.abort()
        panel._controller = null

        const audio = this._getGradVoiceResultAudio(panel)
        if (audio) {
            audio.pause()
            try { audio.currentTime = 0 } catch (e) {}
        }

        if (panel.state === 'pending') panel.state = 'idle'
    },

    sendGradVoiceResultManual(panel) {
        const text = panel._manualInput || ''
        if (!text.trim()) return
        this.rememberPanelInput(panel, '_manualInput', text)
        panel._manualInput = ''
        this._applyGradVoiceResult(panel, text)
    },
}