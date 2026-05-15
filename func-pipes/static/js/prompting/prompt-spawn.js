/*
  prompt-spawn.js
  ─────────────────────────────────────────────────────────────────────────────
  Panel lifecycle: spawn, add by type / catalogue key, remove, reset.
*/

const SpawnMethods = {

    togglePanelFlip(panel) {
        panel.flipped = !panel.flipped
    },

    _spawn(panel) {
        this.panels.push(panel)
        nextTick(() => {
            const el = this.$refs[`panel-${panel.id}`][0]
            stickAll(el)
            dragHost.enable(el)
        })
    },

    _makeAndSpawn(factory, id, preset) {
        this._spawn(makePanel(factory(id, preset)))
    },

    addFromCatalog(key) {
        const preset = COMPONENT_CATALOG.find(c => c.key === key)
        if (!preset) return
        const id = _uid + 1
        if (preset.type === 'text-input')   this._makeAndSpawn(makeTextInputPanel,   id, preset)
        if (preset.type === 'llm')          this._makeAndSpawn(makeLLMPanel,         id, preset)
        if (preset.type === 'audio-record') this._makeAndSpawn(makeAudioRecordPanel, id, preset)
        if (preset.type === 'grad-voice')   this._makeAndSpawn(makeGradVoicePanel,   id, preset)
        if (preset.type === 'grad-voice-result') this._makeAndSpawn(makeGradVoiceResultPanel, id, preset)
        if (preset.type === 'grad-voice-play') this._makeAndSpawn(makeGradVoicePlayPanel, id, preset)
        if (preset.type === 'text-display') this._makeAndSpawn(makeTextDisplayPanel, id, preset)
        if (preset.type === 'transform')    this._makeAndSpawn(makeTransformPanel,   id, preset)
        if (preset.type === 'delay')        this._makeAndSpawn(makeDelayPanel,       id, preset)
        if (preset.type === 'pyfunc')       this._makeAndSpawn(makePyFuncPanel,      id, preset)
        if (preset.type === 'event-input')  this.addEventInput(preset)
    },

    addTextInput()   { const id = _uid + 1; this._makeAndSpawn(makeTextInputPanel,   id) },
    addLLM()         { const id = _uid + 1; this._makeAndSpawn(makeLLMPanel,         id) },
    addAudioRecord() { const id = _uid + 1; this._makeAndSpawn(makeAudioRecordPanel, id) },
    addGradVoice()   { const id = _uid + 1; this._makeAndSpawn(makeGradVoicePanel,   id) },
    addGradVoiceResult() { const id = _uid + 1; this._makeAndSpawn(makeGradVoiceResultPanel, id) },
    addGradVoicePlay() { const id = _uid + 1; this._makeAndSpawn(makeGradVoicePlayPanel, id) },
    addTextDisplay() { const id = _uid + 1; this._makeAndSpawn(makeTextDisplayPanel, id) },
    addTransform()   { const id = _uid + 1; this._makeAndSpawn(makeTransformPanel,   id) },
    addDelay()       { const id = _uid + 1; this._makeAndSpawn(makeDelayPanel,       id) },
    addPyFunc()      { const id = _uid + 1; this._makeAndSpawn(makePyFuncPanel,      id) },

    addEventInput(preset) {
        const id    = _uid + 1
        const panel = makePanel(makeEventInputPanel(id, preset || {}))
        this.panels.push(panel)
        nextTick(() => {
            const el = this.$refs[`panel-${panel.id}`][0]
            stickAll(el)
            dragHost.enable(el)
            this.mountEventInput(panel)
        })
    },

    removePanel(i) {
        const p = this.panels[i]
        if (this.focusPinState?.active && p?._focusPinned) {
            this.clearFocusedPanels()
        }
        // Abort any in-flight LLM request
        if (p.type === 'llm' && p._chat) p._chat.abort()
        if (p.type === 'audio-record') this.cancelAudioRecord(p)
        if (p.type === 'grad-voice') this.stopGradVoice(p)
        if (p.type === 'grad-voice-result') this.stopGradVoiceResult(p)
        if (p.type === 'grad-voice-play') this.stopGradVoicePlay(p)
        // Unmount event listeners
        if (p.type === 'event-input') this.unmountEventInput(p)
        // Emit null from all outbound pips so downstream nodes clear
        ;(p.pipsOutbound || []).forEach(pip => {
            this._emitFromPip(p, pip.index, null)
        })
        this.panels.splice(i, 1)
    },

    resetPanel(panel) {
        if (panel.type === 'text-input') {
            panel.input      = ''
            panel.messages   = []
            panel.lastOutput = null
            panel.state      = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'llm') {
            if (panel._chat) panel._chat.reset()
            panel._chat      = null
            panel.messages   = []
            panel.lastOutput = null
            panel.state      = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'audio-record') {
            this.cancelAudioRecord(panel)
            panel.messages         = []
            panel.lastOutput       = null
            panel.lastError        = null
            panel.lastSavedPath    = ''
            panel.lastResponse     = null
            panel.lastSessionId    = ''
            panel.audioUrl         = ''
            panel.recordedSeconds  = 0
            panel.sampleRate       = 0
            panel._samplesSent     = 0
            panel.state            = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'grad-voice') {
            this.stopGradVoice(panel)
            panel.messages     = []
            panel.lastOutput   = null
            panel.lastError    = null
            panel.lastEventId  = ''
            panel.lastResponse = null
            panel._voiceOverride = ''
            panel._manualInput = ''
            panel.state        = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'grad-voice-result') {
            this.stopGradVoiceResult(panel)
            panel.messages     = []
            panel.lastOutput   = null
            panel.lastError    = null
            panel.lastEventId  = ''
            panel.lastResponse = null
            panel.lastFiles    = []
            panel.audioUrl     = ''
            panel._manualInput = ''
            panel.state        = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'grad-voice-play') {
            this.stopGradVoicePlay(panel)
            panel.messages       = []
            panel.lastText       = ''
            panel.lastOutput     = null
            panel.lastError      = null
            panel.lastEventId    = ''
            panel.lastResponse   = null
            panel.lastFiles      = []
            panel.audioUrl       = ''
            panel._voiceOverride = ''
            panel._manualInput   = ''
            panel.state          = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'text-display') {
            panel.messages = []
            panel.sources  = {}
            panel.state    = 'idle'
        }
        if (panel.type === 'transform') {
            panel.values   = {}
            panel.fnError  = null
            panel.state    = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'delay') {
            // Cancel all pending timers, clear queue
            panel.queue.forEach(entry => clearTimeout(entry.timerId))
            panel.queue  = []
            panel.paused = false
            panel.state  = 'idle'
        }
        if (panel.type === 'pyfunc') {
            panel.values     = {}
            panel.lastOutput = null
            panel.lastError  = null
            panel.state      = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
        if (panel.type === 'event-input') {
            panel.lastDetail   = null
            panel.lastReceived = null
            panel.state        = 'idle'
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
        }
    },
}
