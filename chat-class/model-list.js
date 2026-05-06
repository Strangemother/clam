/**
 * ModelList — fetch available models from an LM Studio / OpenAI-compatible endpoint.
 *
 *   const ml = new ModelList({ endpoint: 'http://192.168.50.60:1234' })
 *   const models = await ml.getList()   // raw model objects
 *   const ids    = await ml.getIds()    // just the id strings
 */
class ModelList {

    constructor(config = {}) {
        // Accept the same config shape as Chat; derive the base host from endpoint.
        const base = (config.endpoint || 'http://localhost:1234')
            .replace(/\/api\/v1\/chat\/?$/, '')   // strip Chat-specific path
            .replace(/\/+$/, '')

        this.baseUrl = base
        this.modelsUrl = `${this.baseUrl}/v1/models`

        this.models = []   // cached after first fetch
    }

    /** Fetch and return the full list of model objects. Caches locally. */
    async getList() {
        const res = await fetch(this.modelsUrl)
        if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
        const data = await res.json()
        this.models = data.data ?? data   // OpenAI wraps in { data: [...] }
        return this.models
    }

    /** Return just the model id strings. Fetches if not yet cached. */
    async getIds() {
        if (!this.models.length) await this.getList()
        return this.models.map(m => m.id)
    }
}
