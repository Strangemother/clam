/*
  core/node-base.js
  ─────────────────────────────────────────────────────────────────────────────
  NodeBase — root class for every graph node in the power-2 system.

  Architecture
  ────────────
  Node state lives in plain reactive Vue objects (panels[]).
  Node *behaviour* lives in static methods on each node class.
  This separation means:
    • Vue reactivity works naturally on plain data objects.
    • Node classes are stateless singletons — easy to extend, test, and load.

  To create a new node type:
    1.  Extend NodeBase (or a suitable subclass like Load).
    2.  Override the static fields: type, label, group, catalog, configFields().
    3.  Override static defaults(id, preset) — call super.defaults() first.
    4.  Override static apply(panel, signal, graph) — your signal logic here.
    5.  Optionally override static tick(panel, dt, graph) for per-frame updates.
    6.  Optionally override static reset(panel, graph).
    7.  Register with NodeRegistry.register(YourClass) at the bottom of the file.
    8.  Load your file in the HTML before index.js.

  Signal format: { v: number (volts), a: number (amps) }  |  null (no power)
*/

const NOMINAL_VOLTS = 240  // W→A conversion baseline shared by all nodes

class NodeBase {

    // ── Sub-classes declare these ───────────────────────────────────────────
    static type    = 'base'
    static label   = 'Node'
    static group   = 'General'

    /**
     * Catalog preset entries for this node type's toolbar dropdown.
     * Each entry is an object spread into defaults() as `preset`.
     * @type {Array<{key: string, label: string, group?: string, [k: string]: any}>}
     */
    static catalog = []

    // ── Initial state factory ───────────────────────────────────────────────

    /**
     * Returns the initial reactive state object for a new panel of this type.
     * Sub-classes should call super.defaults(id, preset) then spread overrides.
     *
     * @param  {number} id      — unique panel ID (also used as pip label)
     * @param  {Object} preset  — catalog preset or {}
     * @returns {Object}
     */
    static defaults(id, preset = {}) {
        return {
            id,
            type:         this.type,
            label:        preset.label || this.label,
            signal:       null,
            powerSources: {},
            state:        'off',
            ripple:       { ...this._defaultRipple() },
            _rippleAccum:  0,
            _rippleOffset: 0,
            pipsInbound:   this._defaultPipsInbound(id),
            pipsOutbound:  this._defaultPipsOutbound(id),
        }
    }

    /** Override to change the default ripple profile for this type. */
    static _defaultRipple() {
        return { enabled: false, amount: 1.0, interval: 1.0 }
    }

    /** Override to suppress inbound pips (e.g. Generator has none). */
    static _defaultPipsInbound(id)  { return [{ label: id, index: 0 }] }

    /** Override to suppress outbound pips (e.g. Bulb is a sink). */
    static _defaultPipsOutbound(id) { return [{ label: id, index: 0 }] }

    // ── Serialisation ───────────────────────────────────────────────────────

    /**
     * List of panel field names to persist in save/load.
     * Runtime state (live, blown, chargeWs …) is excluded deliberately.
     * Sub-classes extend: return [...super.configFields(), 'myField']
     * @returns {string[]}
     */
    static configFields() {
        return ['label']
    }

    // ── Signal processing ───────────────────────────────────────────────────

    /**
     * Process an incoming combined signal and update panel state.
     * Must call graph.emit(panel, outSignal | null) to forward power.
     *
     * @param {Object}      panel  — reactive Vue panel state
     * @param {Object|null} signal — combined { v, a } or null
     * @param {PowerGraph}       graph  — central graph engine (emit, updateAllGenDraws, …)
     */
    static apply(panel, signal, graph) {
        graph.emit(panel, signal)   // default: transparent pass-through
    }

    // ── Per-frame tick ──────────────────────────────────────────────────────

    /**
     * Called every animation frame while the graph is running.
     * Override in sub-classes for capacitor drain, temperature, boot, etc.
     *
     * @param {Object} panel
     * @param {number} dt    — elapsed seconds since last frame (capped ≤ 0.1)
     * @param {PowerGraph}  graph
     */
    static tick(panel, dt, graph) {
        // default: no per-frame work
    }

    // ── Reset ───────────────────────────────────────────────────────────────

    /**
     * Reset panel state to 'off' without altering config fields.
     * Sub-classes should call super.reset(panel, graph) then clear their own extras.
     *
     * @param {Object} panel
     * @param {PowerGraph}  graph
     */
    static reset(panel, graph) {
        panel.signal       = null
        panel.powerSources = {}
        panel.state        = 'off'
        graph.emit(panel, null)
    }
}
