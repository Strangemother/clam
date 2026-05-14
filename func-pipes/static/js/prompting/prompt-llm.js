/*
  prompt-llm.js
  ─────────────────────────────────────────────────────────────────────────────
  LLM node — wraps the Chat class for use in the prompting node graph.

  Each LLM panel holds a Chat instance (created lazily via _getLLMChat).
  When text arrives on the 'in' pip, _applyLLM sends it to the model.
  The response is emitted as { text, meta: { role, model } } on the 'out' pip.

  The 'system' pip carries a system-prompt override: any text received there
  immediately updates the Chat instance's system prompt.

  Prompt management:
    - selectPrompt(panel, path) loads a prompt file from the server.
    - renderSystemPrompt(tpl, message, panel) renders a Jinja2 template server-side.
    - Templated mode re-renders the system prompt with each incoming message.
*/

const LLMMethods = {

    _scrollLLMMessages(panel) {
        nextTick(() => {
            const ref = this.$refs[`msgs-${panel.id}`]
            const el = Array.isArray(ref) ? ref[0] : ref
            if (!el) return
            el.scrollTop = el.scrollHeight
        })
    },

    _describePromptNode(panel) {
        if (!panel) return null
        return {
            id: panel.id,
            name: panel.title || panel.label || `Node ${panel.id}`,
            type: panel.type,
        }
    },

    _describePromptPip(pip, direction = null) {
        if (!pip) return null
        return {
            index: pip.index,
            name: pip.name,
            direction,
        }
    },

    _collectPromptEdges(panel) {
        const empty = { inbound: [], outbound: [] }
        if (!panel) return empty

        const allConns = typeof pipesWalker !== 'undefined' ? (pipesWalker.connections || {}) : {}
        const findPanel = (panelId) => this.panels.find(p => String(p.id) === String(panelId)) || null
        const findConnKey = (conn) => Object.keys(allConns).find(key => allConns[key] === conn) || null
        const inboundConnections = []

        if (typeof pipesWalker !== 'undefined') {
            pipesWalker.getConnections(String(panel.id)).forEach(conn => {
                const { sender, receiver } = conn.obj
                let sourceId = sender.label
                let destinationId = receiver.label
                let sourcePipIndex = sender.pipIndex ?? 0
                let destinationPipIndex = receiver.pipIndex ?? 0

                if (sender.direction === 'inbound') {
                    sourceId = receiver.label
                    destinationId = sender.label
                    sourcePipIndex = receiver.pipIndex ?? 0
                    destinationPipIndex = sender.pipIndex ?? 0
                }

                if (String(destinationId) !== String(panel.id)) return

                const sourcePanel = findPanel(sourceId)
                inboundConnections.push({
                    key: findConnKey(conn),
                    node: this._describePromptNode(sourcePanel),
                    pip: this._describePromptPip(
                        sourcePanel?.pipsOutbound?.find(pip => pip.index === sourcePipIndex) || null,
                        'outbound'
                    ),
                    receiverPipIndex: destinationPipIndex,
                })
            })
        }

        const inbound = (panel.pipsInbound || []).map(pip => ({
            key: `${panel.id}:inbound:${pip.index}`,
            source: this._describePromptPip(pip, 'inbound'),
            sourcePip: this._describePromptPip(pip, 'inbound'),
            destination: this._describePromptNode(panel),
            destinationPip: this._describePromptPip(pip, 'inbound'),
            connections: inboundConnections.filter(conn => conn.receiverPipIndex === pip.index),
        }))

        const outbound = (panel.pipsOutbound || []).map(pip => {
            const connections = typeof pipesWalker !== 'undefined'
                ? this._getOutboundConns(panel, pip.index).map(({ inLabel, inPip, connKey }) => {
                    const destinationPanel = findPanel(inLabel)
                    return {
                        key: connKey,
                        node: this._describePromptNode(destinationPanel),
                        pip: this._describePromptPip(
                            destinationPanel?.pipsInbound?.find(candidate => candidate.index === inPip) || null,
                            'inbound'
                        ),
                    }
                })
                : []

            return {
                key: `${panel.id}:outbound:${pip.index}`,
                source: this._describePromptNode(panel),
                sourcePip: this._describePromptPip(pip, 'outbound'),
                destination: this._describePromptPip(pip, 'outbound'),
                destinationPip: this._describePromptPip(pip, 'outbound'),
                connections,
            }
        })

        return { inbound, outbound }
    },

    /* ── Chat instance management ──────────────────────────────────── */

    _getLLMChat(panel) {
        // Resolve the actual endpoint URL and wire format from endpointKey.
        // Proxy services route through Flask; direct services are called straight.
        let resolvedEndpoint = panel.endpoint || DEFAULT_ENDPOINT
        let chatFormat = 'lmstudio'
        const key = panel.endpointKey
        if (key) {
            const endpoints = this.endpoints   // Vue reactive data — safe to read here
            const cfg = Array.isArray(endpoints) ? endpoints.find(e => e.key === key) : null
            if (cfg) {
                if (cfg.proxy) {
                    resolvedEndpoint = `${PROMPTING_API_BASE}/proxy/?service=${encodeURIComponent(key)}`
                } else if (cfg.url) {
                    resolvedEndpoint = cfg.url   // direct endpoint: use the configured chat URL as-is
                }
                chatFormat = cfg.api_format || 'lmstudio'
            }
        }

        if (!panel._chat
            || panel._chat.options.endpoint !== resolvedEndpoint
            || panel._chat.options.format   !== chatFormat) {
            panel._chat = new Chat({
                endpoint: resolvedEndpoint,
                model:    panel.model,
                system:   panel.prompt?.content || panel._pendingSystem || '',
                format:   chatFormat,
            })
        }
        panel._chat.options.model    = panel.model
        panel._chat.options.endpoint = resolvedEndpoint  // keep in sync on key change
        panel._chat.options.format   = chatFormat
        // Priority: system pip override > loaded prompt file > pending > empty
        const sysOverride = panel._systemOverride ?? panel.prompt?.content ?? panel._pendingSystem ?? ''
        panel._chat.options.system = sysOverride
        if (panel._pendingSystem !== undefined) delete panel._pendingSystem
        return panel._chat
    },

    /* ── core processor called by prompt-signal.js ──────────────────── */

    async _applyLLM(panel, text, meta = {}) {
        if (!text || panel.state === 'pending') return

        panel.messages.push({ role: 'user', content: text })
        panel.state = 'pending'
        this._scrollLLMMessages(panel)

        try {
            const chat = this._getLLMChat(panel)

            // Render system prompt as Jinja2 template if templated mode is on
            if (panel.mode === 'prompt' && panel.templated && panel.prompt?.content) {
                const rendered = await this._renderSystemPrompt(panel.prompt.content, text, panel)
                if (rendered !== null) chat.options.system = rendered
            }

            let reply
            if (panel.mode === 'prompt') {
                reply = await chat.prompt(text)
            } else {
                reply = await chat.send(text)
            }

            if (reply) {
                panel.messages.push({ role: 'assistant', content: reply.content })
                panel.state    = 'idle'
                const sig      = { text: reply.content, meta: { role: 'assistant', model: panel.model } }
                panel.lastOutput = sig
                this._scrollLLMMessages(panel)
                this._emitFromNode(panel, sig)
            }
        } catch (e) {
            if (e?.name !== 'AbortError') {
                const detail = e.data?.error || e.data?.message || e.message
                panel.messages.push({ role: 'error', content: `Error: ${detail}` })
                this._scrollLLMMessages(panel)
                console.error('[LLM error]', e.message, e.data ?? '')
            }
            panel.state = e?.name === 'AbortError' ? 'idle' : 'error'
        }
    },

    stopLLM(panel) {
        if (panel._chat) panel._chat.abort()
        panel.state = 'idle'
    },

    addLLMOutboundPip(panel) {
        const nextIndex = panel.pipsOutbound.length
            ? Math.max(...panel.pipsOutbound.map(pip => pip.index)) + 1
            : 0
        panel.pipsOutbound.push({ label: panel.id, index: nextIndex, name: `out${nextIndex}` })
    },

    removeLLMOutboundPip(panel, index) {
        const pipIndex = panel.pipsOutbound.findIndex(pip => pip.index === index)
        if (pipIndex === -1) return
        this._emitFromPip(panel, index, null)
        panel.pipsOutbound.splice(pipIndex, 1)
    },

    /* ── prompt file loading ────────────────────────────────────────── */

    async selectPrompt(panel, promptPath) {
        panel.promptPath = promptPath || ''
        if (!promptPath) {
            panel.prompt      = null
            panel.promptTitle = ''
            panel.description = ''
            if (panel._chat) {
                panel._chat.options.system = ''
                if (panel.mode === 'chat') panel._chat.reset()
            }
            return
        }
        try {
            const res  = await fetch(`${PROMPTING_API_BASE}/prompts/${promptPath}`)
            const data = await res.json()
            panel.prompt      = { path: promptPath, content: data.content, title: data.title }
            panel.promptTitle = data.title || promptPath
            panel.description = data.description || ''
            // Apply immediately if a Chat instance exists
            if (panel._chat) {
                panel._chat.options.system = data.content
                if (panel.mode === 'chat') panel._chat.reset()
            }
        } catch (e) {
            console.error('[LLM selectPrompt]', e)
        }
    },

    async _renderSystemPrompt(template, message, panel) {
        try {
            const vars = {
                message,
                edges: this._collectPromptEdges(panel),
            }
            const res = await fetch(`${PROMPTING_API_BASE}/prompts/render`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ template, vars }),
            })
            const data = await res.json()
            if (data.error) { console.error('[renderSystemPrompt]', data.error); return null }
            return data.rendered
        } catch (e) {
            console.error('[renderSystemPrompt]', e)
            return null
        }
    },

    /* ── endpoint list ──────────────────────────────────────────────── */

    async fetchEndpoints() {
        try {
            const res       = await fetch(`${PROMPTING_API_BASE}/endpoints/`)
            this.endpoints  = await res.json()
        } catch (e) {
            console.error('[fetchEndpoints]', e)
        }
    },

    /* ── model list ─────────────────────────────────────────────────── */

    async fetchModels() {
        this.fetching = true
        try {
            // Only direct (non-proxy) endpoints expose a model list.
            const selectedEp = (this.endpoints || []).find(e => e.key === this.modelsEndpointKey)
            if (selectedEp?.proxy) {
                console.warn('[fetchModels] proxy endpoints do not expose a model list')
                return
            }
            const ep = (selectedEp?.models_url) || this.modelsEndpoint || DEFAULT_ENDPOINT
            const ml = new ModelList({ endpoint: ep })
            ml.onResult = (models) => { this.modelIds = models.map(m => m.id) }
            await ml.getList()
        } catch (e) {
            console.error('[fetchModels]', e)
        } finally {
            this.fetching = false
        }
    },

    async fetchPrompts() {
        try {
            const res     = await fetch(`${PROMPTING_API_BASE}/prompts/`)
            this.prompts  = await res.json()
        } catch (e) {
            console.error('[fetchPrompts]', e)
        }
    },

    /* ── convenience send helpers called from the template ─────────── */

    // Called by the text-input node's Send button / Enter key
    sendTextInput(panel) {
        const text = (panel.input || '').trim()
        if (!text) return
        panel.input = ''
        panel.messages.push({ role: 'user', text })
        const sig = { text, meta: { role: 'user' } }
        panel.lastOutput = sig
        this._emitFromNode(panel, sig)
    },

    // Called by the LLM node's manual test textarea
    sendLLMManual(panel) {
        const text = (panel._manualInput || '').trim()
        if (!text || panel.state === 'pending') return
        panel._manualInput = ''
        this._applyLLM(panel, text)
    },
}
