/**
 * Chat — wraps a single LLM conversation against the LM Studio native API.
 *
 * POST /api/v1/chat
 * Conversation history is tracked server-side via previous_response_id.
 * Local this.messages is a client-side display log only.
 *
 *   const chat = new Chat({ model: 'granite-4-micro', system: 'You are helpful.' })
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
            metadata: {},
            ...options,
        }

        this.messages          = []       // local display log: [{ role, content }, ...]
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
     * Appends user + assistant turns to local this.messages.
     * Returns the assistant message { role, content }.
     */
    async send(text) {
        this.messages.push({ role: 'user', content: text })

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
        const payload = this.buildPayload(text, { chain: false })
        return this._post(payload)
    }

    /**
     * Build the raw request body.
     * chain: true  → includes previous_response_id (continues conversation)
     * chain: false → standalone request
     */
    buildPayload(text, { chain = false } = {}) {
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
        // LM Studio native response:
        // { output: [{ type: 'message'|'reasoning'|'tool_call', content }], response_id, stats }
        const messageItem = data.output.find(o => o.type === 'message')
        const msg = { role: 'assistant', content: messageItem.content }

        this.lastRaw      = data
        this.lastResponse = msg
        this._responseId  = data.response_id ?? null   // chain future send() calls

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
