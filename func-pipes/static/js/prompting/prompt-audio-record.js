/*
  prompt-audio-record.js
  ─────────────────────────────────────────────────────────────────────────────
  Browser microphone recorder node.

  The node records microphone PCM in the browser, streams it directly to the
  standalone audio_record_server.py websocket service, then emits the saved
  file path downstream once the service confirms the WAV file is written.
*/

const AudioRecordMethods = {

    _scrollAudioRecordMessages(panel) {
        nextTick(() => {
            const ref = this.$refs[`msgs-${panel.id}`]
            const el = Array.isArray(ref) ? ref[0] : ref
            if (!el) return
            el.scrollTop = el.scrollHeight
        })
    },

    _pushAudioRecordMessage(panel, role, content) {
        panel.messages.push({ role, content: String(content == null ? '' : content) })
        this._scrollAudioRecordMessages(panel)
    },

    _mixAudioRecordBuffer(inputBuffer) {
        const channelCount = Math.max(1, Number(inputBuffer.numberOfChannels) || 1)
        const length = inputBuffer.length || 0
        const mono = new Float32Array(length)

        for (let channel = 0; channel < channelCount; channel += 1) {
            const samples = inputBuffer.getChannelData(channel)
            for (let i = 0; i < length; i += 1) {
                mono[i] += samples[i] / channelCount
            }
        }

        return mono
    },

    _encodeAudioRecordChunk(inputBuffer) {
        const mono = this._mixAudioRecordBuffer(inputBuffer)
        const view = new DataView(new ArrayBuffer(mono.length * 2))

        for (let i = 0; i < mono.length; i += 1) {
            const sample = Math.max(-1, Math.min(1, mono[i]))
            const int16 = sample < 0 ? Math.round(sample * 0x8000) : Math.round(sample * 0x7fff)
            view.setInt16(i * 2, int16, true)
        }

        return view.buffer
    },

    _cleanupAudioRecordCapture(panel) {
        if (panel._processorNode) {
            panel._processorNode.onaudioprocess = null
            try { panel._processorNode.disconnect() } catch (e) { console.debug('[AudioRecord disconnect processor]', e) }
        }
        if (panel._sourceNode) {
            try { panel._sourceNode.disconnect() } catch (e) { console.debug('[AudioRecord disconnect source]', e) }
        }
        if (panel._monitorGain) {
            try { panel._monitorGain.disconnect() } catch (e) { console.debug('[AudioRecord disconnect monitor]', e) }
        }
        if (panel._stream) {
            panel._stream.getTracks().forEach(track => {
                try { track.stop() } catch (e) { console.debug('[AudioRecord stop track]', e) }
            })
        }
        if (panel._audioContext && typeof panel._audioContext.close === 'function') {
            panel._audioContext.close().catch(() => {})
        }

        panel._processorNode = null
        panel._sourceNode = null
        panel._monitorGain = null
        panel._stream = null
        panel._audioContext = null
    },

    _closeAudioRecordSocket(panel, code = 1000, reason = 'done') {
        const socket = panel._socket
        panel._socket = null
        panel._socketToken = ''
        panel._expectedSocketClose = true

        if (!socket) return

        socket.onopen = null
        socket.onmessage = null
        socket.onerror = null
        socket.onclose = null

        try {
            if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
                socket.close(code, reason)
            }
        } catch (e) {
            console.debug('[AudioRecord close socket]', e)
        }
    },

    _failAudioRecord(panel, message) {
        panel.lastError = String(message || 'Audio recording failed')
        panel.state = 'error'
        this._cleanupAudioRecordCapture(panel)
        this._closeAudioRecordSocket(panel, 1011, 'error')
        this._pushAudioRecordMessage(panel, 'error', `Error: ${panel.lastError}`)
    },

    _handleAudioRecordSocketMessage(panel, raw) {
        let data
        try {
            data = typeof raw === 'string' ? JSON.parse(raw) : raw
        } catch (e) {
            this._failAudioRecord(panel, 'Invalid recorder response')
            return
        }

        const type = String(data?.type || '').trim().toLowerCase()

        if (type === 'started') {
            panel.lastSessionId = String(data.session_id || '').trim()
            const sampleRate = Number(data.sample_rate)
            if (sampleRate > 0) panel.sampleRate = sampleRate
            return
        }

        if (type === 'saved') {
            this._cleanupAudioRecordCapture(panel)
            panel.lastError = null
            panel.lastResponse = data
            panel.lastSessionId = String(data.session_id || '').trim()
            panel.lastSavedPath = String(data.path || '').trim()
            panel.audioUrl = String(data.public_url || '').trim()
            panel.recordedSeconds = Number(data.duration_seconds) || panel.recordedSeconds || 0
            panel.sampleRate = Number(data.sample_rate) || panel.sampleRate || 0
            panel.state = 'idle'

            const outputText = panel.lastSavedPath || panel.audioUrl || String(data.filename || '').trim()
            panel.lastOutput = {
                text: outputText,
                meta: {
                    role: 'assistant',
                    service: 'audio-record',
                    path: panel.lastSavedPath || null,
                    public_url: panel.audioUrl || null,
                    filename: data.filename || null,
                    duration_seconds: data.duration_seconds ?? null,
                    sample_rate: data.sample_rate ?? null,
                    channels: data.channels ?? null,
                    bytes: data.bytes ?? null,
                },
            }

            this._pushAudioRecordMessage(panel, 'assistant', outputText)
            this._emitFromNode(panel, panel.lastOutput)
            this._closeAudioRecordSocket(panel)
            return
        }

        if (type === 'cancelled') {
            panel.state = 'idle'
            this._cleanupAudioRecordCapture(panel)
            this._closeAudioRecordSocket(panel)
            return
        }

        if (type === 'error') {
            this._failAudioRecord(panel, data?.message || 'Recorder server error')
            return
        }
    },

    async startAudioRecord(panel) {
        if (!panel || (panel.state !== 'idle' && panel.state !== 'error')) return

        const wsUrl = String(panel.wsUrl || '').trim() || DEFAULT_AUDIO_RECORD_WS
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext

        if (!navigator?.mediaDevices?.getUserMedia) {
            this._failAudioRecord(panel, 'Microphone capture is not available in this browser')
            return
        }
        if (!AudioContextCtor) {
            this._failAudioRecord(panel, 'Web Audio API is not available in this browser')
            return
        }

        panel.lastError = null
        panel.lastSavedPath = ''
        panel.audioUrl = ''
        panel.lastResponse = null
        panel.lastSessionId = ''
        panel.recordedSeconds = 0
        panel.sampleRate = 0
        panel._samplesSent = 0
        panel.state = 'connecting'
        this._pushAudioRecordMessage(panel, 'status', `connecting to ${wsUrl}…`)

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const audioContext = new AudioContextCtor()
            if (audioContext.state === 'suspended' && typeof audioContext.resume === 'function') {
                await audioContext.resume().catch(() => {})
            }

            const socket = new WebSocket(wsUrl)
            const token = `${panel.id}-${Date.now()}-${Math.random().toString(16).slice(2)}`
            socket.binaryType = 'arraybuffer'

            panel._socket = socket
            panel._socketToken = token
            panel._expectedSocketClose = false
            panel._stream = stream
            panel._audioContext = audioContext
            panel.sampleRate = Number(audioContext.sampleRate) || 48000

            const connected = new Promise((resolve, reject) => {
                const onOpen = () => {
                    cleanup()
                    resolve()
                }
                const onError = () => {
                    cleanup()
                    reject(new Error('Recorder WebSocket connection failed'))
                }
                const cleanup = () => {
                    socket.removeEventListener('open', onOpen)
                    socket.removeEventListener('error', onError)
                }
                socket.addEventListener('open', onOpen)
                socket.addEventListener('error', onError)
            })

            socket.onmessage = event => {
                if (panel._socketToken !== token) return
                this._handleAudioRecordSocketMessage(panel, event.data)
            }

            socket.onerror = () => {
                if (panel._socketToken !== token || panel.state === 'idle' || panel.state === 'error') return
                this._failAudioRecord(panel, 'Recorder WebSocket error')
            }

            socket.onclose = () => {
                if (panel._socketToken !== token) return

                const expectedClose = panel._expectedSocketClose
                panel._socket = null
                panel._socketToken = ''

                if (expectedClose) return
                if (panel.state !== 'idle' && panel.state !== 'error') {
                    this._failAudioRecord(panel, 'Recorder connection closed unexpectedly')
                }
            }

            await connected

            if (panel._socket !== socket || panel._socketToken !== token) {
                this._cleanupAudioRecordCapture(panel)
                this._closeAudioRecordSocket(panel)
                return
            }

            socket.send(JSON.stringify({
                type: 'start',
                session_id: `panel-${panel.id}-${Date.now()}`,
                sample_rate: panel.sampleRate,
                channels: 1,
                sample_width: 2,
                prefix: panel.filePrefix || 'mic-record',
            }))

            const sourceNode = audioContext.createMediaStreamSource(stream)
            const inputChannels = sourceNode.channelCount || 1
            const processorNode = audioContext.createScriptProcessor(4096, inputChannels, 1)
            const monitorGain = audioContext.createGain()
            monitorGain.gain.value = 0

            processorNode.onaudioprocess = event => {
                if (panel._socket !== socket || socket.readyState !== WebSocket.OPEN || panel.state !== 'recording') return

                const chunk = this._encodeAudioRecordChunk(event.inputBuffer)
                if (!chunk || !chunk.byteLength) return

                socket.send(chunk)
                panel._samplesSent += Math.floor(chunk.byteLength / 2)
                const sampleRate = Number(panel.sampleRate) || 48000
                panel.recordedSeconds = sampleRate
                    ? Number((panel._samplesSent / sampleRate).toFixed(1))
                    : 0
            }

            sourceNode.connect(processorNode)
            processorNode.connect(monitorGain)
            monitorGain.connect(audioContext.destination)

            panel._sourceNode = sourceNode
            panel._processorNode = processorNode
            panel._monitorGain = monitorGain
            panel.state = 'recording'
            this._pushAudioRecordMessage(panel, 'status', `recording at ${panel.sampleRate} Hz…`)

        } catch (e) {
            this._failAudioRecord(panel, e?.message || String(e))
        }
    },

    stopAudioRecord(panel) {
        if (!panel || panel.state !== 'recording') return

        const socket = panel._socket
        this._cleanupAudioRecordCapture(panel)

        if (!socket || socket.readyState !== WebSocket.OPEN) {
            this._failAudioRecord(panel, 'Recorder connection is not open')
            return
        }

        panel.state = 'saving'
        try {
            socket.send(JSON.stringify({ type: 'stop' }))
        } catch (e) {
            this._failAudioRecord(panel, e?.message || 'Failed to stop recorder')
        }
    },

    cancelAudioRecord(panel) {
        if (!panel) return

        const socket = panel._socket
        this._cleanupAudioRecordCapture(panel)

        if (socket && socket.readyState === WebSocket.OPEN) {
            try { socket.send(JSON.stringify({ type: 'cancel' })) } catch (e) { console.debug('[AudioRecord cancel]', e) }
        }

        this._closeAudioRecordSocket(panel)
        if (panel.state !== 'error') panel.state = 'idle'
    },
}