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
    - renderSystemPrompt(tpl, message) renders a Jinja2 template server-side.
    - Templated mode re-renders the system prompt with each incoming message.
*/

const LLMMethods = {

    /* ── Chat instance management ──────────────────────────────────── */

    _getLLMChat(panel) {
        if (!panel._chat || panel._chat.options.endpoint !== panel.endpoint) {
            panel._chat = new Chat({
                endpoint: panel.endpoint,
                model:    panel.model,
                system:   panel.prompt?.content || panel._pendingSystem || '',
            })
        }
        panel._chat.options.model  = panel.model
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

        try {
            const chat = this._getLLMChat(panel)

            // Render system prompt as Jinja2 template if templated mode is on
            if (panel.mode === 'prompt' && panel.templated && panel.prompt?.content) {
                const rendered = await this._renderSystemPrompt(panel.prompt.content, text)
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
                this._emitFromPip(panel, 0, sig)   // pip index 0 = 'out'
            }
        } catch (e) {
            if (e?.name !== 'AbortError') {
                panel.messages.push({ role: 'error', content: `Error: ${e.message}` })
            }
            panel.state = e?.name === 'AbortError' ? 'idle' : 'error'
        }
    },

    stopLLM(panel) {
        if (panel._chat) panel._chat.abort()
        panel.state = 'idle'
    },

    /* ── prompt file loading ────────────────────────────────────────── */

    async selectPrompt(panel, promptPath) {
        if (!promptPath) {
            panel.prompt      = null
            panel.description = ''
            if (panel._chat) panel._chat.options.system = ''
            return
        }
        try {
            const res  = await fetch(`${PROMPTING_API_BASE}/prompts/${promptPath}`)
            const data = await res.json()
            panel.prompt      = { path: promptPath, content: data.content, title: data.title }
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

    async _renderSystemPrompt(template, message) {
        try {
            const res = await fetch(`${PROMPTING_API_BASE}/prompts/render`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ template, vars: { message } }),
            })
            const data = await res.json()
            if (data.error) { console.error('[renderSystemPrompt]', data.error); return null }
            return data.rendered
        } catch (e) {
            console.error('[renderSystemPrompt]', e)
            return null
        }
    },

    /* ── model list ─────────────────────────────────────────────────── */

    async fetchModels() {
        this.fetching = true
        try {
            const ep = this.modelsEndpoint || DEFAULT_ENDPOINT
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
