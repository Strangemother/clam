/*
  prompt-grad-voice.js
  ─────────────────────────────────────────────────────────────────────────────
  Grad Voice node — sends inbound text to the Flask backend, which proxies the
  positional Gradio payload expected by the speech service.

  Flow:
    1. inbound signal arrives on pip 'in'
    2. panel voice comes from the dropdown or the named 'voice' inbound pip
    3. POST /prompting/grad-voice/ { text, voice }
    3. emit the returned event_id on outbound pip 'out'
*/

const DEFAULT_GRAD_VOICE_OPTIONS = [
    { value: 'af_bella', label: 'Bella (af_bella)' },
    { value: 'bf_emma', label: 'Emma (bf_emma)' },
]

const GradVoiceMethods = {

    async fetchGradVoiceVoices() {
        this.fetchingGradVoiceVoices = true
        try {
            const res = await fetch(`${PROMPTING_API_BASE}/grad-voice/voices/`)
            const data = await res.json().catch(() => ({}))
            const voices = Array.isArray(data.voices) && data.voices.length
                ? data.voices
                : DEFAULT_GRAD_VOICE_OPTIONS

            this.gradVoiceVoices = voices
        } catch (e) {
            console.error('[fetchGradVoiceVoices]', e)
            this.gradVoiceVoices = DEFAULT_GRAD_VOICE_OPTIONS
        } finally {
            this.fetchingGradVoiceVoices = false
        }
    },

    setGradVoiceVoiceOverride(panel, value) {
        panel._voiceOverride = String(value == null ? '' : value).trim()
    },

    getGradVoiceEffectiveVoice(panel) {
        const pipVoice = String(panel._voiceOverride || '').trim()
        const selectedVoice = String(panel.voice || '').trim()
        return pipVoice || selectedVoice || DEFAULT_GRAD_VOICE_VOICE
    },

    _scrollGradVoiceMessages(panel) {
        nextTick(() => {
            const ref = this.$refs[`msgs-${panel.id}`]
            const el = Array.isArray(ref) ? ref[0] : ref
            if (!el) return
            el.scrollTop = el.scrollHeight
        })
    },

    async _applyGradVoice(panel, text, meta = {}) {
        const spokenText = text == null ? '' : String(text)
        if (!spokenText.trim() || panel.state === 'pending') return

        const selectedVoice = this.getGradVoiceEffectiveVoice(panel)

        panel.messages.push({ role: meta?.role || 'user', content: spokenText })
        panel.state = 'pending'
        panel.lastError = null
        this._scrollGradVoiceMessages(panel)

        if (panel._controller) panel._controller.abort()
        panel._controller = new AbortController()

        try {
            const res = await fetch(`${PROMPTING_API_BASE}/grad-voice/`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ text: spokenText, voice: selectedVoice }),
                signal:  panel._controller.signal,
            })
            const data = await res.json().catch(() => ({}))

            if (!res.ok) {
                const detail = data.error
                    || data.response?.detail?.[0]?.msg
                    || data.response?.error
                    || data.message
                    || `request failed (${res.status})`
                throw Object.assign(new Error(String(detail)), { data })
            }

            const eventId = String(data.event_id || data.response?.event_id || '').trim()
            const outputText = eventId || JSON.stringify(data.response ?? data)

            panel.lastEventId = eventId
            panel.lastResponse = data.response ?? data
            panel.messages.push({ role: 'assistant', content: outputText })
            panel.state = 'idle'

            const sig = {
                text: outputText,
                meta: {
                    role: 'assistant',
                    service: 'grad-voice',
                    event_id: eventId || null,
                    voice: selectedVoice,
                    response: panel.lastResponse,
                },
            }
            panel.lastOutput = sig
            this._scrollGradVoiceMessages(panel)
            this._emitFromNode(panel, sig)

        } catch (e) {
            if (e?.name !== 'AbortError') {
                panel.lastError = e.message
                panel.messages.push({ role: 'error', content: `Error: ${e.message}` })
                panel.state = 'error'
                this._scrollGradVoiceMessages(panel)
                console.error('[GradVoice error]', e.message, e.data ?? '')
            } else {
                panel.state = 'idle'
            }
        } finally {
            panel._controller = null
        }
    },

    stopGradVoice(panel) {
        if (panel._controller) panel._controller.abort()
        panel._controller = null
        if (panel.state === 'pending') panel.state = 'idle'
    },

    sendGradVoiceManual(panel) {
        const text = panel._manualInput || ''
        if (!text.trim() || panel.state === 'pending') return
        this.rememberPanelInput(panel, '_manualInput', text)
        panel._manualInput = ''
        this._applyGradVoice(panel, text)
    },
}