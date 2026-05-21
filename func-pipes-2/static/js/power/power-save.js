/*
  power-save.js
  ─────────────
  Save and restore the full layout of the power backbone simulation.

  Exported as a global `PowerSave` object — no build step required.

  Two primary operations
  ──────────────────────
  PowerSave.save(panels, refs)
      Captures panel config, X/Y positions, and wire connections into a
      JSON blob and writes it to localStorage. Returns the JSON string so
      callers can also offer a file download.

  PowerSave.loadFromStorage()  →  layout object | null
  PowerSave.parseJSON(str)     →  layout object | null
      Parse a layout object from localStorage or a supplied JSON string.
      The layout object is what you pass to the Vue app's _restoreLayout().

  Layout schema
  ─────────────
  {
    nodes: [
      {
        id:     <number>        — original panel id (preserved on restore)
        type:   <string>        — gen | breaker | bulb | load | meter
        title:  <string>        — displayed header
        config: { …type fields } — only the configurable values
        pos:    { left, top }   — CSS px strings, relative to #panels parent
      }
    ],
    connections: [
      { sender: { label, direction, pipIndex }, receiver: { … }, line: { … } }
    ]
  }
*/

const PowerSave = (() => {

    const STORAGE_KEY = 'power-backbone-layout'

    // ── configurable fields per node type ───────────────────────────────────
    // Runtime state (live, state, blown, chargeWs …) is intentionally excluded;
    // the simulation restarts clean from the saved configuration.
    const CONFIG_FIELDS = {
        gen:       ['label', 'volts', 'amps', 'live', 'ripple'],
        breaker:   ['label', 'ratingAmps'],
        bulb:      ['label', 'watts', 'maxVolts'],
        load:      ['label', 'watts', 'minVolts', 'maxVolts', 'capacitance', 'ripple'],
        meter:     ['label'],
        converter: ['label', 'outVolts', 'step', 'efficiency', 'ripple'],
    }

    // ── internal helpers ─────────────────────────────────────────────────────

    function _readPos(panelId, refs) {
        const ref = refs[`panel-${panelId}`]
        const el  = Array.isArray(ref) ? ref[0] : ref
        if (!el) return { left: '20px', top: '20px' }
        return {
            left: el.style.left || '20px',
            top:  el.style.top  || '20px',
        }
    }

    function _readConnections() {
        // pipesWalker.connections holds the same object reference as pipeData.connections
        // inside pipes-runtime.js (pipeData is IIFE-scoped and not exported).
        if (typeof pipesWalker === 'undefined' || !pipesWalker.connections) return []
        return Object.values(pipesWalker.connections).map(c => c.obj).filter(Boolean)
    }

    // ── export ───────────────────────────────────────────────────────────────

    /**
     * Build a layout object from live app state.
     * @param {Array}  panels — Vue app's this.panels
     * @param {Object} refs   — Vue app's this.$refs
     * @returns {Object} layout
     */
    function toObject(panels, refs, edges = null) {
        const nodes = panels.map(p => {
            const fields = CONFIG_FIELDS[p.type] || ['label']
            const config = {}
            fields.forEach(f => { config[f] = p[f] })
            return {
                id:     p.id,
                type:   p.type,
                title:  p.title,
                config,
                pos:    _readPos(p.id, refs),
            }
        })
        const layout = { nodes, connections: _readConnections() }
        if (edges) layout.edges = edges
        return layout
    }

    /**
     * Serialise the current layout to a JSON string.
     * Does NOT write to localStorage — use save() for that.
     */
    function toJSON(panels, refs, edges = null) {
        return JSON.stringify(toObject(panels, refs, edges), null, 2)
    }

    /**
     * Export the layout and persist it to localStorage.
     * @returns {string} JSON string (for download or logging)
     */
    function save(panels, refs, edges = null) {
        const json = toJSON(panels, refs, edges)
        try {
            localStorage.setItem(STORAGE_KEY, json)
        } catch (e) {
            console.warn('PowerSave: localStorage write failed', e)
        }
        return json
    }

    // ── import ───────────────────────────────────────────────────────────────

    /**
     * Read and parse the layout previously saved to localStorage.
     * @returns {Object|null} layout object, or null if nothing stored / corrupt
     */
    function loadFromStorage() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY)
            if (!raw) return null
            return JSON.parse(raw)
        } catch (e) {
            console.error('PowerSave: corrupt localStorage entry', e)
            return null
        }
    }

    /**
     * Parse a JSON string into a layout object.
     * @param {string} json
     * @returns {Object|null}
     */
    function parseJSON(json) {
        try {
            return JSON.parse(json)
        } catch (e) {
            console.error('PowerSave: invalid JSON', e)
            return null
        }
    }

    // ── public surface ───────────────────────────────────────────────────────
    return { STORAGE_KEY, toObject, toJSON, save, loadFromStorage, parseJSON }

})()
