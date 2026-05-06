/**
 * Chat — wraps a single LLM conversation against an OpenAI-compatible endpoint.
      
       const chat = new Chat({ endpoint: 'http://localhost:1234/v1/chat/completions/', model: 'llama3.2:latest' })
       await chat.send('Hello')
       await chat.prompt('One-shot question, no history')
 */
class Chat {

    constructor(options = {}) {
        this.options = {
            endpoint:     '/v1/chat/completions/',
            model:        '',
            system:       '',
            stream:       false,
            history:      true,
            maxHistory:   0,
            metadata:     {},
            pollInterval: 500,
            ...options,
        }

        this.messages     = []
        this.state        = 'idle'
        this.lastResponse = null
        this.lastError    = null
        this._handlers    = {}
    }

    // ── public API ────────────────────────────────────────────────────────────

    /** Append user message to history, post, append reply. Returns assistant Message. */
    async send(text) {
        if (this.options.history) {
            this.messages.push({ role: 'user', content: text })
        }

        const payload = this.buildPayload()
        const reply   = await this._post(payload)

        if (this.options.history) {
            this.messages.push(reply)
            this._trimHistory()
        }

        return reply
    }

    /** One-shot prompt — does not touch history. Returns assistant Message. */
    async prompt(text) {
        const payload = this.buildPayload(text)
        return this._post(payload)
    }

    /** Build the request body. Uses current history when text is omitted. */
    buildPayload(userText = null, role = 'user') {
        let messages = this._withSystem(this.messages)

        if (userText !== null) {
            messages = [...messages, { role, content: userText }]
        }

        return {
            model:    this.options.model,
            messages,
            stream:   this.options.stream,
            ...this.options.metadata,
        }
    }

    /** Clear message history. */
    reset(keepSystem = true) {
        this.messages     = []
        this.lastResponse = null
        this.state        = 'idle'

        if (keepSystem && this.options.system) {
            // system is injected at send-time via _withSystem; nothing stored here
        }
    }

    setSystem(text)  { this.options.system = text }
    setModel(name)   { this.options.model  = name }

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

    /** Prepend system message if one is set. */
    _withSystem(messages) {
        if (!this.options.system) return messages
        return [{ role: 'system', content: this.options.system }, ...messages]
    }

    /** Trim history to maxHistory message pairs (user + assistant = 1 pair). */
    _trimHistory() {
        const max = this.options.maxHistory
        if (!max || this.messages.length <= max * 2) return
        this.messages = this.messages.slice(-(max * 2))
    }

    async _post(payload) {
        this._setState('pending')
        this.lastError = null

        try {
            const res  = await fetch(this.options.endpoint, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(payload),
            })

            if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)

            const data = await res.json()

            // receipt-based async pattern (home.html style)
            if (data.receipt_id) {
                return await this._poll(data.receipt_id)
            }

            return this._handleResponse(data)

        } catch (err) {
            this.lastError = err
            this._setState('error')
            this._emit('error', err)
            throw err
        }
    }

    _handleResponse(data) {
        const msg = data.choices[0].message          // { role, content }
        this.lastResponse = msg
        this._setState('idle')
        this._emit('response', msg)
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
