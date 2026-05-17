/*
  prompt-grad-voice-indextts2.js
  ─────────────────────────────────────────────────────────────────────────────
  Dedicated IndexTTS2 Grad Voice node.

  Flow:
    1. inbound signal arrives on pip 'in'
    2. optional ref/emotion audio arrives on named inbound pips
    3. POST /prompting/grad-voice/indextts2/ with dedicated IndexTTS2 options
    4. emit the returned event_id on outbound pip 'out'
*/

const GradVoiceIndexTTS2Methods = {

    _getGradVoiceIndexTTS2UploadInput(panel, kind) {
        const refName = kind === 'emotion'
            ? `indextts2-emotion-upload-${panel.id}`
            : `indextts2-ref-upload-${panel.id}`
        const ref = this.$refs[refName]
        return Array.isArray(ref) ? ref[0] : ref
    },

    _scrollGradVoiceIndexTTS2Messages(panel) {
        nextTick(() => {
            const ref = this.$refs[`msgs-${panel.id}`]
            const el = Array.isArray(ref) ? ref[0] : ref
            if (!el) return
            el.scrollTop = el.scrollHeight
        })
    },

    _extractGradVoiceIndexTTS2Reference(signal) {
        const meta = signal?.meta || {}
        const candidates = [meta.file_data, meta.path, signal?.text]

        for (const candidate of candidates) {
            if (candidate == null) continue

            if (typeof candidate === 'string') {
                const raw = candidate.trim()
                if (raw) return raw
                continue
            }

            if (typeof candidate === 'object') {
                try {
                    return JSON.stringify(candidate)
                } catch (e) {
                    console.warn('[GradVoiceIndexTTS2 stringify]', e)
                }
            }
        }

        return ''
    },

    setGradVoiceIndexTTS2Reference(panel, fieldName, signal) {
        if (!panel || !fieldName) return
        panel[fieldName] = signal == null
            ? ''
            : this._extractGradVoiceIndexTTS2Reference(signal)

        const isEmotionField = fieldName === 'emotionAudioValue'
        const uploadField = isEmotionField ? '_emotionAudioFile' : '_refAudioFile'
        const uploadNameField = isEmotionField ? '_emotionAudioUploadName' : '_refAudioUploadName'
        panel[uploadField] = null
        panel[uploadNameField] = ''

        const input = this._getGradVoiceIndexTTS2UploadInput(panel, isEmotionField ? 'emotion' : 'ref')
        if (input) input.value = ''
    },

    setGradVoiceIndexTTS2Upload(panel, kind, event) {
        const file = event?.target?.files?.[0] || null
        const isEmotion = kind === 'emotion'
        const uploadField = isEmotion ? '_emotionAudioFile' : '_refAudioFile'
        const uploadNameField = isEmotion ? '_emotionAudioUploadName' : '_refAudioUploadName'

        panel[uploadField] = file
        panel[uploadNameField] = file?.name ? String(file.name) : ''
    },

    clearGradVoiceIndexTTS2Upload(panel, kind) {
        const isEmotion = kind === 'emotion'
        const uploadField = isEmotion ? '_emotionAudioFile' : '_refAudioFile'
        const uploadNameField = isEmotion ? '_emotionAudioUploadName' : '_refAudioUploadName'

        panel[uploadField] = null
        panel[uploadNameField] = ''

        const input = this._getGradVoiceIndexTTS2UploadInput(panel, isEmotion ? 'emotion' : 'ref')
        if (input) input.value = ''
    },

    _buildGradVoiceIndexTTS2RequestInit(panel, spokenText) {
        const payload = {
            text: spokenText,
            ref_audio: panel.refAudioValue || null,
            emotion_audio: panel.emotionAudioValue || null,
            options: this._buildGradVoiceIndexTTS2Options(panel),
        }

        const hasUploads = Boolean(panel._refAudioFile || panel._emotionAudioFile)
        if (!hasUploads) {
            return {
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            }
        }

        const formData = new FormData()
        formData.append('text', payload.text)
        formData.append('options', JSON.stringify(payload.options))

        if (payload.ref_audio) formData.append('ref_audio', payload.ref_audio)
        if (payload.emotion_audio) formData.append('emotion_audio', payload.emotion_audio)
        if (panel._refAudioFile) {
            formData.append('ref_audio_upload', panel._refAudioFile, panel._refAudioFile.name || 'ref-audio.bin')
        }
        if (panel._emotionAudioFile) {
            formData.append('emotion_audio_upload', panel._emotionAudioFile, panel._emotionAudioFile.name || 'emotion-audio.bin')
        }

        return { body: formData }
    },

    _buildGradVoiceIndexTTS2Options(panel) {
        return {
            tts_engine: 'IndexTTS2',
            audio_format: 'wav',
            indextts2_emotion_mode: String(panel.emotionMode || DEFAULT_GRAD_VOICE_INDEXTTS2.emotionMode).trim() || DEFAULT_GRAD_VOICE_INDEXTTS2.emotionMode,
            indextts2_emotion_description: String(panel.emotionDescription ?? '').trim(),
            indextts2_emo_alpha: Number(panel.emoAlpha ?? DEFAULT_GRAD_VOICE_INDEXTTS2.emoAlpha),
            indextts2_happy: Number(panel.happy ?? DEFAULT_GRAD_VOICE_INDEXTTS2.happy),
            indextts2_angry: Number(panel.angry ?? DEFAULT_GRAD_VOICE_INDEXTTS2.angry),
            indextts2_sad: Number(panel.sad ?? DEFAULT_GRAD_VOICE_INDEXTTS2.sad),
            indextts2_afraid: Number(panel.afraid ?? DEFAULT_GRAD_VOICE_INDEXTTS2.afraid),
            indextts2_disgusted: Number(panel.disgusted ?? DEFAULT_GRAD_VOICE_INDEXTTS2.disgusted),
            indextts2_melancholic: Number(panel.melancholic ?? DEFAULT_GRAD_VOICE_INDEXTTS2.melancholic),
            indextts2_surprised: Number(panel.surprised ?? DEFAULT_GRAD_VOICE_INDEXTTS2.surprised),
            indextts2_calm: Number(panel.calm ?? DEFAULT_GRAD_VOICE_INDEXTTS2.calm),
            indextts2_temperature: Number(panel.temperature ?? DEFAULT_GRAD_VOICE_INDEXTTS2.temperature),
            indextts2_top_p: Number(panel.topP ?? DEFAULT_GRAD_VOICE_INDEXTTS2.topP),
            indextts2_top_k: Number(panel.topK ?? DEFAULT_GRAD_VOICE_INDEXTTS2.topK),
            indextts2_repetition_penalty: Number(panel.repetitionPenalty ?? DEFAULT_GRAD_VOICE_INDEXTTS2.repetitionPenalty),
            indextts2_max_mel_tokens: Number(panel.maxMelTokens ?? DEFAULT_GRAD_VOICE_INDEXTTS2.maxMelTokens),
            indextts2_seed: Number(panel.seed ?? DEFAULT_GRAD_VOICE_INDEXTTS2.seed),
            indextts2_use_random: Boolean(panel.useRandom),
        }
    },

    async _applyGradVoiceIndexTTS2(panel, text, meta = {}) {
        const spokenText = text == null ? '' : String(text)
        if (!spokenText.trim() || panel.state === 'pending') return

        panel.messages.push({ role: meta?.role || 'user', content: spokenText })
        panel.state = 'pending'
        panel.lastError = null
        this._scrollGradVoiceIndexTTS2Messages(panel)

        if (panel._controller) panel._controller.abort()
        panel._controller = new AbortController()

        try {
            const requestInit = this._buildGradVoiceIndexTTS2RequestInit(panel, spokenText)
            const res = await fetch(`${PROMPTING_API_BASE}/grad-voice/indextts2/`, {
                method:  'POST',
                ...requestInit,
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
                    service: 'grad-voice-indextts2',
                    engine: 'IndexTTS2',
                    event_id: eventId || null,
                    ref_audio: panel.refAudioValue || null,
                    emotion_audio: panel.emotionAudioValue || null,
                    ref_audio_upload: panel._refAudioUploadName || null,
                    emotion_audio_upload: panel._emotionAudioUploadName || null,
                    response: panel.lastResponse,
                },
            }
            panel.lastOutput = sig
            this._scrollGradVoiceIndexTTS2Messages(panel)
            this._emitFromNode(panel, sig)

        } catch (e) {
            if (e?.name !== 'AbortError') {
                panel.lastError = e.message
                panel.messages.push({ role: 'error', content: `Error: ${e.message}` })
                panel.state = 'error'
                this._scrollGradVoiceIndexTTS2Messages(panel)
                console.error('[GradVoiceIndexTTS2 error]', e.message, e.data ?? '')
            } else {
                panel.state = 'idle'
            }
        } finally {
            panel._controller = null
        }
    },

    stopGradVoiceIndexTTS2(panel) {
        if (panel._controller) panel._controller.abort()
        panel._controller = null
        if (panel.state === 'pending') panel.state = 'idle'
    },

    sendGradVoiceIndexTTS2Manual(panel) {
        const text = panel._manualInput || ''
        if (!text.trim() || panel.state === 'pending') return
        this.rememberPanelInput(panel, '_manualInput', text)
        panel._manualInput = ''
        this._applyGradVoiceIndexTTS2(panel, text)
    },
}