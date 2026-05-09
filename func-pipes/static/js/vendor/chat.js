/**
 * Chat — wraps a single LLM conversation.
 *
 * Supports two wire formats, selected via options.format:
 *
 *   'lmstudio' (default)
 *     POST { model, input, system_prompt?, previous_response_id?, stream }
 *     Server tracks history via response_id chain.
 *
 *   'openai'
 *     POST { model, messages: [{role,content},…], stream }
 *     Client sends full history every turn (OpenAI / DO / compatible APIs).
 *
 *   const chat = new Chat({ model: 'gpt-4o', system: 'You are helpful.', format: 'openai' })
 *   await chat.send('Hello')        // continues the conversation
 *   await chat.prompt('One-shot')   // no history, no side-effects
 */
class Chat {

    constructor(options = {}) {
        this.options = {
            endpoint: 'http://localhost:1234/api/v1/chat',
            model:    '',
            system:   '',
            stream:   false,
            format:   'lmstudio',  // 'lmstudio' | 'openai'
            metadata: {},
            ...options,
        }

        this.messages          = []       // conversation history: [{ role, content }, ...]
        this.state             = 'idle'
        this.lastResponse      = null     // last assistant message { role, content }
        this.lastRaw           = null     // full raw API response
        this.lastError         = null
        this._responseId       = null     // previous_response_id for conversation chaining
        this._handlers         = {}
        this._abortController  = null

        // Override to handle responses your way. Default prints to console.
        this.onResponse    = (msg) => console.log(`[${msg.role}]`, msg.content)
    }

    // ── public API ────────────────────────────────────────────────────────────

    /**
     * Send a message, continuing the conversation.
     * Appends user + assistant turns to this.messages.
     * Returns the assistant message { role, content }.
     */
    async send(text) {
        this.messages.push({ role: 'user', content: text })

        // For openai format, buildPayload reads this.messages directly,
        // so the new user turn is already included above.
        const payload = this.buildPayload(text, { chain: true })
        const reply   = await this._post(payload)

        this.messages.push(reply)
        return reply
    }

    /**
     * One-shot prompt — does not affect conversation history or this.messages.
     * Returns the assistant message { role, content }.
     */
    async prompt(text) {
        const payload = this.buildPayload(text, { chain: false, oneshot: true })
        return this._post(payload)
    }

    /**
     * Build the raw request body.
     *
     * For 'lmstudio':
     *   chain: true  → includes previous_response_id
     *   chain: false → standalone, no history
     *
     * For 'openai':
     *   chain: true  → sends full this.messages array (client-side history)
     *   oneshot:true → sends only system + current user message, no history
     */
    buildPayload(text, { chain = false, oneshot = false } = {}) {
        if (this.options.format === 'openai') {
            const messages = []
            if (this.options.system) {
                messages.push({ role: 'system', content: this.options.system })
            }
            if (oneshot || !chain) {
                // One-shot: just this message, no accumulated history
                messages.push({ role: 'user', content: text })
            } else {
                // Full history — this.messages already has the new user turn
                // pushed by send() before buildPayload is called
                messages.push(...this.messages)
            }
            const payload = { messages, stream: this.options.stream }
            if (this.options.model) payload.model = this.options.model
            return payload
        }

        // LM Studio native format
        const payload = {
            model:  this.options.model,
            input:  text,
            stream: this.options.stream,
            ...this.options.metadata,
        }
        if (this.options.system) {
            payload.system_prompt = this.options.system
        }
        if (chain && this._responseId) {
            payload.previous_response_id = this._responseId
        }
        return payload
    }

    /** Cancel any in-flight request. Resets state to idle. */
    abort() {
        if (this._abortController) {
            this._abortController.abort()
            this._abortController = null
        }
        this._setState('idle')
    }

    /** Clear local message log and server-side conversation chain. */
    reset() {
        this.messages    = []
        this.lastResponse = null
        this.lastRaw      = null
        this._responseId  = null
        this.state        = 'idle'
    }

    setSystem(text) { this.options.system = text }
    setModel(name)  { this.options.model  = name }

    /** Register an event handler. Chainable. */
    on(event, handler) {
        (this._handlers[event] ||= []).push(handler)
        return this
    }

    /** Remove a previously registered handler. */
    off(event, handler) {
        if (!this._handlers[event]) return this
        this._handlers[event] = this._handlers[event].filter(h => h !== handler)
        return this
    }

    // ── internals ─────────────────────────────────────────────────────────────

    _emit(event, payload) {
        (this._handlers[event] || []).forEach(h => h(payload))
    }

    _setState(state) {
        this.state = state
        this._emit('update', { state, messages: this.messages })
    }

    async _post(payload) {
        this._setState('pending')
        this.lastError = null

        this._abortController = new AbortController()

        try {
            const res = await fetch(this.options.endpoint, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(payload),
                signal:  this._abortController.signal,
            })

            if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)

            const data = await res.json()
            return this._handleResponse(data)

        } catch (err) {
            if (err.name === 'AbortError') {
                this._setState('idle')
                return null
            }
            this.lastError = err
            this._setState('error')
            this._emit('error', err)
            throw err
        } finally {
            this._abortController = null
        }
    }

    _handleResponse(data) {
        let msg

        if (data.choices) {
            // OpenAI / DO format: { choices: [{ message: { role, content } }] }
            const choice = data.choices[0].message
            msg = { role: choice.role || 'assistant', content: choice.content }
            this._responseId = null   // OpenAI services don't use response chaining
        } else {
            // LM Studio native: { output: [{ type: 'message', content }], response_id }
            const messageItem = data.output.find(o => o.type === 'message')
            msg = { role: 'assistant', content: messageItem.content }
            this._responseId = data.response_id ?? null
        }

        this.lastRaw      = data
        this.lastResponse = msg

        this._setState('idle')
        this._emit('response', msg)
        this.onResponse(msg)
        return msg
    }

    _poll(receiptId) {
        return new Promise((resolve, reject) => {
            const iv = setInterval(async () => {
                try {
                    const res  = await fetch(`/result/${receiptId}/`)
                    const data = await res.json()

                    if (data && data.message) {
                        clearInterval(iv)
                        await fetch(`/clear/${receiptId}/`)
                        resolve(this._handleResponse(data))
                    }
                } catch (err) {
                    clearInterval(iv)
                    this.lastError = err
                    this._setState('error')
                    this._emit('error', err)
                    reject(err)
                }
            }, this.options.pollInterval)
        })
    }
}
