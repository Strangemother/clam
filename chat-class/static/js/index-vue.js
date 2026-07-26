const DEFAULT_ENDPOINT = 'http://192.168.50.60:1234/api/v1/chat/'
const DEFAULT_MODEL    = 'granite-4.0-h-tiny'
const ENDPOINT_STORAGE_KEY = 'chat-class-endpoints'
const MAX_SAVED_ENDPOINTS = 20

const { createApp, nextTick } = Vue

const setupZooming = function() {
    window.infiniteDrag = new ZoomableInfiniteDrag('.layer-space', '.panel', {
        zoomMode: 'transform',
    })
}

/* ── panel factory ────────────────────────────────────────────────────────── */

let _uid = 0

function makePanel(endpoint, model) {
    const id = ++_uid
    return {
        id,
        pipsInbound:  [{ label: id, index: 0 }],
        pipsOutbound: [{ label: id, index: 0 }],
        endpoint: endpoint || DEFAULT_ENDPOINT,
        model:    model    || DEFAULT_MODEL,
        modelIds: [],
        prompt:   null,      // selected prompt { name, path } or null
        mode:     'chat',    // 'chat' (history) | 'prompt' (one-shot) | 'input' (passthrough)
        templated: false,    // render system prompt as Jinja2 template before each send
        input:    '',
        state:    'idle',    // 'idle' | 'pending'
        messages: [],
        description: '',     // from prompt metadata
        showPrompt:  false,   // whether the full system prompt is expanded
        _chat:    null,      // Chat instance, created lazily
    }
}

/* ── app ──────────────────────────────────────────────────────────────────── */
dragHost = new DragSolo()

createApp({

    data() {
        return {
            newEndpoint: DEFAULT_ENDPOINT,
            savedEndpoints: [],
            modelIds:    [],
            endpointModels: {},
            prompts:     [],   // [{ name, path }] loaded from /prompts/
            fetching:    false,
            graphRunning: true,  // false = graph forwarding paused
            panels:      [],
        }
    },

    async mounted() {
        setupZooming()
        this.loadSavedEndpoints()
        this.fetchModels()
        this.fetchPrompts()
    },

    methods: {

        loadSavedEndpoints() {
            try {
                const stored = JSON.parse(localStorage.getItem(ENDPOINT_STORAGE_KEY) || '[]')
                this.savedEndpoints = Array.isArray(stored)
                    ? stored.filter(endpoint => typeof endpoint === 'string' && endpoint.trim())
                    : []
            } catch (e) {
                console.error('[Endpoints]', e)
                this.savedEndpoints = []
            }
        },

        rememberEndpoint(endpoint) {
            const value = String(endpoint || '').trim()
            if (!value) return

            this.savedEndpoints = [
                value,
                ...this.savedEndpoints.filter(saved => saved !== value),
            ].slice(0, MAX_SAVED_ENDPOINTS)
            localStorage.setItem(ENDPOINT_STORAGE_KEY, JSON.stringify(this.savedEndpoints))
        },

        /* Fetch prompt file list from the server */
        async fetchPrompts() {
            try {
                const res = await fetch('/prompts/')
                this.prompts = await res.json()
            } catch (e) {
                console.error('[Prompts]', e)
            }
        },

        /* Return the cache key used for model lists and endpoint requests. */
        endpointKey(endpoint) {
            return new ModelList({ endpoint }).baseUrl
        },

        /* Fetch and cache models for one endpoint. */
        async fetchModelsForEndpoint(endpoint, force = false) {
            const key = this.endpointKey(endpoint)
            if (!force && this.endpointModels[key]) {
                return this.endpointModels[key]
            }

            const ml = new ModelList({ endpoint })
            const models = await ml.getList()
            const ids = models.map(model => model.id)
            this.endpointModels[key] = ids
            return ids
        },

        /* Fetch the toolbar endpoint and update only panels using that endpoint. */
        async fetchModels() {
            this.fetching = true
            try {
                this.rememberEndpoint(this.newEndpoint)
                const key = this.endpointKey(this.newEndpoint)
                const ids = await this.fetchModelsForEndpoint(this.newEndpoint, true)
                this.modelIds = ids
                this.panels.forEach(panel => {
                    if (this.endpointKey(panel.endpoint) === key) {
                        this.applyPanelModels(panel, ids)
                    }
                })
            } catch (e) {
                console.error('[ModelList]', e)
            } finally {
                this.fetching = false
            }
        },

        /* Populate a panel from its endpoint and retain a valid selection. */
        async loadPanelModels(panel, force = false) {
            const endpoint = panel.endpoint
            const key = this.endpointKey(endpoint)
            try {
                const ids = await this.fetchModelsForEndpoint(endpoint, force)
                if (this.endpointKey(panel.endpoint) !== key) return
                this.applyPanelModels(panel, ids)
            } catch (e) {
                if (this.endpointKey(panel.endpoint) === key) {
                    panel.modelIds = []
                }
                console.error('[ModelList]', e)
            }
        },

        applyPanelModels(panel, ids) {
            panel.modelIds = [...ids]
            if (!panel.modelIds.includes(panel.model)) {
                panel.model = panel.modelIds[0] || ''
            }
        },

        panelEndpointChanged(panel) {
            this.rememberEndpoint(panel.endpoint)
            panel._chat?.reset()
            this.loadPanelModels(panel, true)
        },

        addPanel()    {
            this.rememberEndpoint(this.newEndpoint)
            let panel = makePanel(this.newEndpoint)
            this.panels.push(panel)
            this.loadPanelModels(panel)

            setTimeout(()=>{
                let n = this._.refs[`panel-${panel.id}`][0]
                stickAll(n)
                dragHost.enable(n)
            }, 100)
        },

        addInputPanel() {
            this.rememberEndpoint(this.newEndpoint)
            let panel = makePanel(this.newEndpoint)
            panel.mode = 'input'
            this.panels.push(panel)
            this.loadPanelModels(panel)

            setTimeout(()=>{
                let n = this._.refs[`panel-${panel.id}`][0]
                stickAll(n)
                dragHost.enable(n)
            }, 100)
        },

        removePanel(i){
            this.panels.splice(i, 1)
        },

        /* Return (or recreate) the Chat instance for a panel.
           Recreates if the endpoint has changed since last call. */
        getChat(panel) {
            if (!panel._chat || panel._chat.options.endpoint !== panel.endpoint) {
                panel._chat = new Chat({ endpoint: panel.endpoint, model: panel.model })
            }
            panel._chat.options.model  = panel.model
            panel._chat.options.system = panel.prompt?.content || ''

            panel._chat.onResponse = (msg) => {
                panel.messages.push(msg)
                panel.state = 'idle'
                this.scrollToBottom(panel)
                // Forward response to downstream connected panels
                if (this.graphRunning && typeof pipesWalker !== 'undefined') {
                    const ids = pipesWalker.getOutgoingIds(String(panel.id))
                    ids.forEach(targetId => {
                        const target = this.panels.find(p => String(p.id) === String(targetId))
                        if (target) this.sendMessageText(target, msg.content)
                    })
                }
            }

            return panel._chat
        },

        /* Load prompt content from server and apply to panel */
        async selectPrompt(panel, promptPath) {
            if (!promptPath) {
                panel.prompt = null
                panel.description = ''
                return
            }
            try {
                const res  = await fetch(`/prompts/${promptPath}`)
                const data = await res.json()
                panel.prompt = { path: promptPath, content: data.content, title: data.title }
                panel.description = data.description || ''
                // Reset conversation so new system prompt takes effect cleanly
                panel._chat?.reset()
            } catch (e) {
                console.error('[Prompt load]', e)
            }
        },

        /* Send the current input text as a user message */
        async sendMessage(panel) {
            const text = panel.input.trim()
            if (!text || panel.state === 'pending') return
            panel.input = ''
            await this.sendMessageText(panel, text)
        },

        /* Send an arbitrary text to a panel (used by sendMessage + pipe forwarding) */
        async sendMessageText(panel, text) {
            if (!text || panel.state === 'pending') return
            panel.messages.push({ role: 'user', content: text })
            this.scrollToBottom(panel)

            // Input-only mode: forward directly downstream without hitting an LLM
            if (panel.mode === 'input') {
                if (this.graphRunning && typeof pipesWalker !== 'undefined') {
                    const ids = pipesWalker.getOutgoingIds(String(panel.id))
                    ids.forEach(targetId => {
                        const target = this.panels.find(p => String(p.id) === String(targetId))
                        if (target) this.sendMessageText(target, text)
                    })
                }
                return
            }

            panel.state = 'pending'
            try {
                const chat = this.getChat(panel)
                // If templated mode, render the system prompt server-side first
                if (panel.mode === 'prompt' && panel.templated && panel.prompt?.content) {
                    const rendered = await this.renderSystemPrompt(panel.prompt.content, text)
                    if (rendered !== null) chat.options.system = rendered
                }
                panel.mode === 'prompt'
                    ? await chat.prompt(text)
                    : await chat.send(text)
            } catch (e) {
                if (e?.name !== 'AbortError') {
                    panel.messages.push({ role: 'status', content: `Error: ${e.message}` })
                }
                panel.state = 'idle'
            }
        },

        /* Render a Jinja2 system prompt template via the server.
           Returns the rendered string, or null on error. */
        async renderSystemPrompt(template, message) {
            try {
                const res = await fetch('/prompts/render', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        template,
                        vars: { message },
                    }),
                })
                const data = await res.json()
                if (data.error) { console.error('[Render]', data.error); return null }
                return data.rendered
            } catch (e) {
                console.error('[Render]', e)
                return null
            }
        },

        /* Copy a message's text to the clipboard */
        copyMessage(m) {
            navigator.clipboard.writeText(m.content).catch(e => console.error('[Copy]', e))
        },

        /* Reset a panel's conversation history */
        resetPanel(panel) {
            panel.messages = []
            panel._chat?.reset()
        },

        /* Cancel an in-flight request on a panel */
        stopPanel(panel) {
            panel._chat?.abort()
            panel.state = 'idle'
        },

        /* Pause/resume graph forwarding */
        toggleGraph() {
            this.graphRunning = !this.graphRunning
        },

        /* ── pip drag-and-drop ──────────────────────────────────────────── */

        pipStartDrag(event, direction, pip) {
            event.target.classList.add('dragging')
            event.dataTransfer.clearData()
            event.dataTransfer.setData('text/plain', JSON.stringify({
                label: pip.label, direction, pipIndex: pip.index
            }))
        },

        pipEndDrag(event, direction, pip) {
            event.target.classList.remove('dragging')
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        },

        pipOverDrag(event, direction, pip) {
            event.preventDefault()
        },

        pipDrop(event, direction, pip) {
            const sender   = JSON.parse(event.dataTransfer.getData('text/plain'))
            const receiver = { label: pip.label, direction, pipIndex: pip.index }
            this.connect(sender, receiver)
        },

        connect(sender, receiver) {
            const palette = ['#e6194b','#3cb44b','#ffe119','#4363d8',
                             '#f58231','#911eb4','#46f0f0','#f032e6']
            const line = {
                color: palette[Math.floor(Math.random() * palette.length)],
                width: Math.floor(Math.random() * 4) + 2,
            }
            document.dispatchEvent(new CustomEvent('connectnodes', {
                detail: { sender, receiver, line }
            }))
            if (typeof dispatchRequestDrawEvent !== 'undefined') dispatchRequestDrawEvent()
        },

        scrollToBottom(panel) {
            nextTick(() => {
                const el = this.$refs['msgs-' + panel.id]?.[0]
                if (el) el.scrollTop = el.scrollHeight
            })
        },
    },

}).mount('#app')
