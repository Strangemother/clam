/*
  prompt-persist.js
  ─────────────────────────────────────────────────────────────────────────────
    Save / restore layout to localStorage, server route, or JSON file.
  Mirrors inputs-persist.js; serialises prompt-specific fields.
*/

const STORAGE_KEY = 'prompting-layout-v1'

const PersistMethods = {

    async saveLayout() {
        const json = this._toJSON()
        const name = (this.layoutName || '').trim()

        if (name) {
            const encodedName = name.split('/').map(part => encodeURIComponent(part)).join('/')
            this.savingLayout = true
            try {
                const res = await fetch(`${PROMPTING_API_BASE}/layouts/${encodedName}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: json,
                })
                const data = await res.json().catch(() => ({}))
                if (!res.ok) {
                    throw new Error(data.error || String(res.status))
                }
                console.info('PromptSave: layout saved to server:', data.path || name)
                return json
            } catch (e) {
                console.warn('PromptSave: server save failed', e)
            } finally {
                this.savingLayout = false
            }
        }

        localStorage.setItem(STORAGE_KEY, json)
        console.info('PromptSave: layout saved (%d nodes)', this.panels.length)
        return json
    },

    exportJSON() {
        const json = this._toJSON()
        const a    = document.createElement('a')
        a.href     = 'data:application/json,' + encodeURIComponent(json)
        a.download = 'prompting-layout.json'
        a.click()
    },

    async loadLayout(json = null) {
        if (!this.prompts?.length && typeof this.fetchPrompts === 'function') {
            await this.fetchPrompts()
        }

        if (json !== null) {
            const layout = this._parseLayout(json)
            if (layout) await this._restoreLayout(layout)
            return
        }

        const name = (this.layoutName || '').trim()
        if (name) {
            const encodedName = name.split('/').map(part => encodeURIComponent(part)).join('/')
            this.loadingLayout = true
            try {
                const res = await fetch(`${PROMPTING_API_BASE}/layouts/${encodedName}`)
                const src = await res.text()
                if (!res.ok) throw new Error(src || String(res.status))
                const layout = this._parseLayout(src)
                if (layout) {
                    await this._restoreLayout(layout)
                    console.info('PromptSave: layout loaded from server:', name)
                }
            } catch (e) {
                console.warn('PromptSave: server load failed', e)
            } finally {
                this.loadingLayout = false
            }
            return
        }

        const src = localStorage.getItem(STORAGE_KEY)
        if (!src) { console.warn('PromptSave: nothing to load'); return }
        const layout = this._parseLayout(src)
        if (layout) await this._restoreLayout(layout)
    },

    importJSON() {
        const input  = document.createElement('input')
        input.type   = 'file'
        input.accept = '.json,application/json'
        input.onchange = e => {
            const file = e.target.files[0]
            if (!file) return
            const reader = new FileReader()
            reader.onload = ev => this.loadLayout(ev.target.result)
            reader.readAsText(file)
        }
        input.click()
    },

    // ── internal ──────────────────────────────────────────────────────

    _parseLayout(src) {
        if (!src) return null
        if (typeof src === 'string') {
            try {
                return JSON.parse(src)
            } catch (e) {
                console.warn('PromptSave: invalid layout JSON', e)
                return null
            }
        }
        if (typeof src === 'object') return src
        console.warn('PromptSave: unsupported layout payload', typeof src)
        return null
    },

    _toJSON() {
        const nodes = this.panels.map(p => {
            const ref = this.$refs[`panel-${p.id}`]
            const el  = Array.isArray(ref) ? ref[0] : ref
            const pos = el
                ? (window.infiniteDrag?.getPersistedBox?.(el) || {
                    left:   el.style.left || `${el.offsetLeft}px`,
                    top:    el.style.top  || `${el.offsetTop}px`,
                    width:  el.style.width  || `${el.offsetWidth}px`,
                    height: el.style.height || `${el.offsetHeight}px`,
                })
                : null

            let config
            if (p.type === 'llm') {
                config = {
                    label:        p.label,
                    endpointKey:  p.endpointKey,
                    endpoint:     p.endpoint,
                    model:        p.model,
                    mode:         p.mode,
                    templated:    p.templated,
                    promptPath:   p.promptPath || p.prompt?.path || null,
                    promptTitle:  p.promptTitle || p.prompt?.title || null,
                    outputs:      p.pipsOutbound.map(pip => ({ name: pip.name, index: pip.index })),
                }
            } else if (p.type === 'audio-record') {
                config = {
                    label:      p.label,
                    wsUrl:      p.wsUrl,
                    filePrefix: p.filePrefix,
                }
            } else if (p.type === 'grad-voice') {
                config = {
                    label: p.label,
                    voice: p.voice,
                }
            } else if (p.type === 'grad-voice-indextts2') {
                config = {
                    label: p.label,
                    refAudioValue: p.refAudioValue,
                    emotionAudioValue: p.emotionAudioValue,
                    emotionMode: p.emotionMode,
                    emotionDescription: p.emotionDescription,
                    emoAlpha: p.emoAlpha,
                    happy: p.happy,
                    angry: p.angry,
                    sad: p.sad,
                    afraid: p.afraid,
                    disgusted: p.disgusted,
                    melancholic: p.melancholic,
                    surprised: p.surprised,
                    calm: p.calm,
                    temperature: p.temperature,
                    topP: p.topP,
                    topK: p.topK,
                    repetitionPenalty: p.repetitionPenalty,
                    maxMelTokens: p.maxMelTokens,
                    seed: p.seed,
                    useRandom: p.useRandom,
                }
            } else if (p.type === 'grad-voice-play') {
                config = {
                    label:    p.label,
                    voice:    p.voice,
                    autoPlay: p.autoPlay,
                }
            } else if (p.type === 'text-display') {
                config = {
                    label:      p.label,
                    latestOnly: p.latestOnly,
                }
            } else if (p.type === 'wait') {
                config = {
                    label:       p.label,
                    delayMs:     p.delayMs,
                    waitMessage: p.waitMessage,
                }
            } else if (p.type === 'sync') {
                config = {
                    label:          p.label,
                    countWatermark: p.countWatermark,
                    delayMs:        p.delayMs,
                    emitList:       p.emitList,
                    inputs:         p.pipsInbound.map(pip => ({ name: pip.name, index: pip.index })),
                }
            } else if (p.type === 'transform') {
                config = {
                    label:       p.label,
                    inputs:      p.pipsInbound.map(pip  => ({ name: pip.name,  index: pip.index })),
                    outputs:     p.pipsOutbound.map(pip => ({ name: pip.name,  index: pip.index })),
                    fnSrc:       p.fnSrc,
                    gatePip:     p.gatePip,
                    gateMode:    p.gateMode,
                    gatePattern: p.gatePattern,
                }
            } else if (p.type === 'event-input') {
                config = {
                    label:     p.label,
                    eventName: p.eventName,
                    outputs:   p.pipsOutbound.map(pip => ({ name: pip.name, index: pip.index })),
                }
            } else if (p.type === 'grad-voice-result') {
                config = {
                    label:    p.label,
                    autoPlay: p.autoPlay,
                }
            } else {
                config = { label: p.label }
            }

            if (p.flipped) {
                config.flipped = true
            }

            return { id: p.id, type: p.type, title: p.title || p.label, config, pos }
        })

        const connections = []
        if (typeof pipesWalker !== 'undefined' && pipesWalker.connections) {
            Object.values(pipesWalker.connections).forEach(conn => {
                connections.push({ sender: conn.obj.sender, receiver: conn.obj.receiver })
            })
        }

        return JSON.stringify({ nodes, connections }, null, 2)
    },

    async _restoreLayout(layout) {
        if (!layout?.nodes) return

        if (window.infiniteDrag?.resetViewState) {
            window.infiniteDrag.resetViewState()
        }

        this._clearAll()
        await nextTick()

        const factoryMap = {
            'text-input':   makeTextInputPanel,
            'llm':          makeLLMPanel,
            'audio-record': makeAudioRecordPanel,
            'grad-voice':   makeGradVoicePanel,
            'grad-voice-indextts2': makeGradVoiceIndexTTS2Panel,
            'grad-voice-result': makeGradVoiceResultPanel,
            'grad-voice-play': makeGradVoicePlayPanel,
            'text-display': makeTextDisplayPanel,
            'wait':         makeWaitPanel,
            'sync':         makeSyncPanel,
            'transform':    makeTransformPanel,
            'delay':        makeDelayPanel,
            'pyfunc':       makePyFuncPanel,
            'event-input':  makeEventInputPanel,
        }
        const maxId = Math.max(0, ...layout.nodes.map(n => n.id))
        const promptLoads = []

        for (const node of layout.nodes) {
            _uid = node.id - 1
            const factory = factoryMap[node.type]
            if (!factory) continue
            const panel = makePanel(factory(node.id, node.config || {}))
            if (node.title) panel.title = node.title
            panel.flipped = Boolean(node.config?.flipped)
            this._spawn(panel)

            // Re-load prompt content if it was saved
            if (node.type === 'llm' && node.config?.promptPath) {
                promptLoads.push(this.selectPrompt(panel, node.config.promptPath))
            }
            // Re-mount event listener
            if (node.type === 'event-input') {
                nextTick(() => this.mountEventInput(panel))
            }
        }
        _uid = maxId

        if (promptLoads.length) {
            await Promise.all(promptLoads)
        }

        await nextTick()
        await nextTick()

        layout.nodes.forEach(node => {
            const ref = this.$refs[`panel-${node.id}`]
            const el  = Array.isArray(ref) ? ref[0] : ref
            if (el && node.pos) {
                el.style.left = node.pos.left
                el.style.top  = node.pos.top
                if (node.pos.width)  el.style.width  = node.pos.width
                if (node.pos.height) el.style.height = node.pos.height
            }
        })

        for (const obj of (layout.connections || [])) {
            const sEl = document.getElementById(
                `${obj.sender.label}-${obj.sender.direction}-${obj.sender.pipIndex}`)
            const rEl = document.getElementById(
                `${obj.receiver.label}-${obj.receiver.direction}-${obj.receiver.pipIndex}`)
            if (sEl && rEl) {
                this.connect(obj.sender, obj.receiver)
            } else {
                console.warn('PromptSave: skipping connection — pip not found', obj)
            }
        }
    },

    _clearAll() {
        if (typeof this.resetFocusPinState === 'function') {
            this.resetFocusPinState()
        }
        this.panels.forEach(p => {
            if (p.type === 'llm' && p._chat) p._chat.abort()
            if (p.type === 'audio-record') this.cancelAudioRecord(p)
            if (p.type === 'grad-voice') this.stopGradVoice(p)
            if (p.type === 'grad-voice-indextts2') this.stopGradVoiceIndexTTS2(p)
            if (p.type === 'grad-voice-result') this.stopGradVoiceResult(p)
            if (p.type === 'grad-voice-play') this.stopGradVoicePlay(p)
            if (p.type === 'wait') this.stopWait(p)
            if (p.type === 'sync') this.stopSync(p)
            if (p.type === 'event-input') this.unmountEventInput(p)
        })
        this.panels = []
        if (typeof pipesWalker !== 'undefined' && pipesWalker.connections) {
            Object.keys(pipesWalker.connections).forEach(k => delete pipesWalker.connections[k])
        }
        if (typeof clItems !== 'undefined') {
            clItems.layers.forEach(layer => { layer.lines = {} })
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        }
    },
}
