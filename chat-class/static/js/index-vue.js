const DEFAULT_ENDPOINT = 'http://192.168.50.60:1234/api/v1/chat/'
const DEFAULT_MODEL    = 'granite-4.0-h-tiny'

const { createApp, nextTick } = Vue

/* ── panel factory ────────────────────────────────────────────────────────── */

let _uid = 0

function makePanel(endpoint, model) {
    return {
        id:       ++_uid,
        endpoint: endpoint || DEFAULT_ENDPOINT,
        model:    model    || DEFAULT_MODEL,
        prompt:   null,      // selected prompt { name, path } or null
        input:    '',
        state:    'idle',    // 'idle' | 'pending'
        messages: [],
        _chat:    null,      // Chat instance, created lazily
    }
}

/* ── app ──────────────────────────────────────────────────────────────────── */
dragHost = new DragSolo()

createApp({

    data() {
        return {
            newEndpoint: DEFAULT_ENDPOINT,
            modelIds:    [],
            prompts:     [],   // [{ name, path }] loaded from /prompts/
            fetching:    false,
            panels:      [],
        }
    },

    async mounted() {
        this.fetchModels()
        this.fetchPrompts()
    },

    methods: {

        /* Fetch prompt file list from the server */
        async fetchPrompts() {
            try {
                const res = await fetch('/prompts/')
                this.prompts = await res.json()
            } catch (e) {
                console.error('[Prompts]', e)
            }
        },

        /* Fetch model list and populate all model dropdowns */
        async fetchModels() {
            this.fetching = true
            try {
                const ml = new ModelList({ endpoint: this.newEndpoint })
                ml.onResult = (models) => { this.modelIds = models.map(m => m.id) }
                await ml.getList()
            } catch (e) {
                console.error('[ModelList]', e)
            } finally {
                this.fetching = false
            }
        },

        addPanel()    {
            let panel = makePanel(this.newEndpoint)
            this.panels.push(panel)

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
            }

            return panel._chat
        },

        /* Load prompt content from server and apply to panel */
        async selectPrompt(panel, promptPath) {
            if (!promptPath) {
                panel.prompt = null
                return
            }
            try {
                const res  = await fetch(`/prompts/${promptPath}`)
                const text = await res.text()
                panel.prompt = { path: promptPath, content: text }
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

            panel.messages.push({ role: 'user', content: text })
            panel.input = ''
            panel.state = 'pending'
            this.scrollToBottom(panel)

            try {
                await this.getChat(panel).send(text)
            } catch (e) {
                panel.messages.push({ role: 'status', content: `Error: ${e.message}` })
                panel.state = 'idle'
            }
        },

        scrollToBottom(panel) {
            nextTick(() => {
                const el = this.$refs['msgs-' + panel.id]?.[0]
                if (el) el.scrollTop = el.scrollHeight
            })
        },
    },

}).mount('#app')
