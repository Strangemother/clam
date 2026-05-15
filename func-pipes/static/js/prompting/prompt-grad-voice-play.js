/*
  prompt-grad-voice-play.js
  ─────────────────────────────────────────────────────────────────────────────
  Combined Grad Voice node — receives text, submits it to the backend, waits
  for completion, resolves the first audio file, and can play it immediately.
*/

const GradVoicePlayMethods = {

    _scrollGradVoicePlayMessages(panel) {
        nextTick(() => {
            const ref = this.$refs[`msgs-${panel.id}`]
            const el = Array.isArray(ref) ? ref[0] : ref
            if (!el) return
            el.scrollTop = el.scrollHeight
        })
    },

    _getGradVoicePlayAudio(panel) {
        const ref = this.$refs[`audio-${panel.id}`]
        return Array.isArray(ref) ? ref[0] : ref
    },

    async _applyGradVoicePlay(panel, text, meta = {}) {
        const spokenText = text == null ? '' : String(text)
        if (!spokenText.trim() || panel.state === 'pending') return

        const selectedVoice = this.getGradVoiceEffectiveVoice(panel)

        panel.lastText = spokenText
        panel.messages.push({ role: meta?.role || 'user', content: spokenText })
        panel.state = 'pending'
        panel.lastError = null
        this._scrollGradVoicePlayMessages(panel)

        if (panel._controller) panel._controller.abort()
        panel._controller = new AbortController()

        try {
            const res = await fetch(`${PROMPTING_API_BASE}/grad-voice/generate/`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ text: spokenText, voice: selectedVoice }),
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
            const eventId = String(data.event_id || data.submit?.event_id || '').trim()
            const audioUrl = String(data.first_file_url || files[0]?.proxy_url || '').trim()
            const outputText = audioUrl || JSON.stringify(data.payloads ?? data)

            panel.lastEventId = eventId
            panel.lastResponse = data
            panel.lastFiles = files
            panel.audioUrl = audioUrl
            panel.messages.push({ role: 'assistant', content: outputText })
            panel.state = 'idle'

            const sig = {
                text: outputText,
                meta: {
                    role: 'assistant',
                    service: 'grad-voice-play',
                    event_id: eventId || null,
                    voice: selectedVoice,
                    files,
                    response: data,
                },
            }
            panel.lastOutput = sig
            this._scrollGradVoicePlayMessages(panel)
            this._emitFromNode(panel, sig)

            if (panel.autoPlay && panel.audioUrl) {
                await this.playGradVoicePlay(panel)
            }

        } catch (e) {
            if (e?.name !== 'AbortError') {
                panel.lastError = e.message
                panel.messages.push({ role: 'error', content: `Error: ${e.message}` })
                panel.state = 'error'
                this._scrollGradVoicePlayMessages(panel)
                console.error('[GradVoicePlay error]', e.message, e.data ?? '')
            } else {
                panel.state = 'idle'
            }
        } finally {
            panel._controller = null
        }
    },

    async playGradVoicePlay(panel) {
        if (!panel.audioUrl) return

        await nextTick()

        const el = this._getGradVoicePlayAudio(panel)
        if (!el) return

        try {
            el.currentTime = 0
            await el.play()
        } catch (e) {
            panel.lastError = `play failed: ${e.message}`
            console.warn('[GradVoicePlay play]', e)
        }
    },

    stopGradVoicePlay(panel) {
        if (panel._controller) panel._controller.abort()
        panel._controller = null

        const audio = this._getGradVoicePlayAudio(panel)
        if (audio) {
            audio.pause()
            try { audio.currentTime = 0 } catch (e) {}
        }

        if (panel.state === 'pending') panel.state = 'idle'
    },

    sendGradVoicePlayManual(panel) {
        const text = panel._manualInput || ''
        if (!text.trim() || panel.state === 'pending') return
        panel._manualInput = ''
        this._applyGradVoicePlay(panel, text)
    },

    regenerateGradVoicePlay(panel) {
        const text = String(panel.lastText || '').trim()
        if (!text || panel.state === 'pending') return
        this._applyGradVoicePlay(panel, text, { role: 'user' })
    },
}