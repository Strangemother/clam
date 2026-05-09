/*
  prompting/index.js  (app shell)
  ────────────────────────────────
  Thin entry point — bootstraps the Vue app and composes all method groups.

  Load order in prompting.html:
    nodes.js → prompt-spawn.js → prompt-signal.js → prompt-llm.js →
      prompt-wiring.js → prompt-persist.js → prompt-transform.js →
      prompt-pyfunc.js → prompt-event.js → index.js
*/

const { createApp, nextTick } = Vue

let _uid = 0

// ── panel factory ─────────────────────────────────────────────────────────────
function makePanel(overrides = {}) {
    const id = ++_uid
    return Object.assign({ id, title: overrides.label || `Node ${id}` }, overrides)
}

// ── group catalogue helper ────────────────────────────────────────────────────
function catalogByGroup() {
    const groups = {}
    COMPONENT_CATALOG.forEach(c => {
        if (!groups[c.group]) groups[c.group] = []
        groups[c.group].push(c)
    })
    return groups
}

dragHost = new DragSolo()

createApp({

    data() {
        return {
            panels:           [],
            catalogGroups:    catalogByGroup(),
            disconnectMode:   false,
            disconnectFirst:  null,
            transformPresets: TRANSFORM_PRESETS,
            // LLM toolbar state
            endpoints:          [],               // loaded from /prompting/endpoints/
            modelsEndpointKey:  DEFAULT_ENDPOINT_KEY,
            modelsEndpoint:     DEFAULT_ENDPOINT, // fallback free-text (legacy)
            modelIds:           [],
            prompts:            [],
            fetching:           false,
            // PyFunc toolbar state
            pyFunctions:        [],
            fetchingFunctions:  false,
        }
    },

    async mounted() {
        await this.fetchEndpoints()
        await this.fetchPrompts()
        await this.fetchFunctions()
        // Models must be fetched manually via the toolbar after setting the endpoint.
    },

    methods: {
        ...SpawnMethods,
        ...SignalMethods,
        ...LLMMethods,
        ...WiringMethods,
        ...PersistMethods,
        ...TransformMethods,
        ...PyFuncMethods,
        ...EventMethods,
    },

}).mount('#app')
