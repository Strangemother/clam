/*
  prompt-pyfunc.js
  ─────────────────────────────────────────────────────────────────────────────
  PyFunc node — calls Python functions from pyfuncs.py via the backend API.

  Flow:
    1. fetchFunctions()  — GET /prompting/functions/ → populates this.pyFunctions
    2. selectPyFunc(panel, fnName)
           — copies param list from pyFunctions into panel.pipsInbound
           — rebuilds panel.values
    3. callPyFunc(panel)  (also _callPyFunc for auto-call from signal)
           — POST /prompting/functions/call { function, params }
           — emits { text: result, meta: { fn } } on outbound pip 0
*/

const PyFuncMethods = {

    /* ── function list ──────────────────────────────────────────────── */

    async fetchFunctions() {
        this.fetchingFunctions = true
        try {
            const res          = await fetch(`${PROMPTING_API_BASE}/functions/`)
            this.pyFunctions   = await res.json()
        } catch (e) {
            console.error('[fetchFunctions]', e)
        } finally {
            this.fetchingFunctions = false
        }
    },

    /* ── select a function → rebuild pips ───────────────────────────── */

    selectPyFunc(panel, fnName) {
        const def = this.pyFunctions.find(f => f.name === fnName)
        if (!def) return

        panel.fnName     = fnName
        panel.lastError  = null
        panel.state      = 'idle'

        // Rebuild inbound pips to match the function's parameters
        panel.pipsInbound = def.params.map((p, i) => ({
            label: panel.id,
            index: i,
            name:  p.name,
            ptype: p.type,
        }))

        // Seed values from existing values where name matches, clear the rest
        const prev    = { ...panel.values }
        panel.values  = {}
        def.params.forEach(p => {
            panel.values[p.name] = prev[p.name] ?? (p.default !== undefined ? p.default : '')
        })

        // Disconnect wires on any pips that no longer exist — let the user
        // re-wire; old pip DOM elements will be removed by Vue's v-for.
    },

    /* ── call the function ──────────────────────────────────────────── */

    // Called from the panel's "Call" button (no leading underscore — Vue 3)
    async callPyFunc(panel) {
        if (!panel.fnName || panel.state === 'running') return

        Object.entries(panel.values || {}).forEach(([name, value]) => {
            this.rememberPanelInput(panel, `values:${name}`, value)
        })

        return this._callPyFunc(panel)
    },

    async _callPyFunc(panel) {
        if (!panel.fnName || panel.state === 'running') return

        panel.state     = 'running'
        panel.lastError = null

        try {
            const res  = await fetch(`${PROMPTING_API_BASE}/functions/call`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    function: panel.fnName,
                    params:   { ...panel.values },
                }),
            })
            const data = await res.json()

            if (data.error) {
                panel.lastError = data.error
                panel.state     = 'error'
                return
            }

            panel.state      = 'idle'
            const sig        = { text: String(data.result), meta: { fn: panel.fnName } }
            panel.lastOutput = sig
            this._emitFromPip(panel, 0, sig)

        } catch (e) {
            panel.lastError = e.message
            panel.state     = 'error'
        }
    },
}
