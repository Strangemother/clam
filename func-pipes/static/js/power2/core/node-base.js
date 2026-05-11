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
            enabled:      true,         // off-switch: false = unit disabled, no outbound signal
            signal:       null,
            powerSources: {},
            state:        'off',
            ripple:       { ...this._defaultRipple() },
            spike:        { ...this._defaultSpike() },
            _rippleAccum:  0,
            _rippleOffset: 0,
            _spikeTimer:   0,
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

    // ── Spike (inrush current) helpers ─────────────────────────────────────

    /** Override in subclasses to set startup inrush spike defaults for this type. */
    static _defaultSpike() {
        return { enabled: false, percent: 0, duration: 0.5 }
    }

    /** Begin an inrush spike at the moment a node turns on. No-op if disabled. */
    static startSpike(panel) {
        if (!panel.spike?.enabled || !panel.spike.percent) return
        panel._spikeTimer = panel.spike.duration ?? 0.5
    }

    /**
     * Decay the spike timer by dt. Returns true if the spike is still active.
     * Call once per tick() frame.
     */
    static tickSpike(panel, dt) {
        if (!panel._spikeTimer || panel._spikeTimer <= 0) return false
        panel._spikeTimer = Math.max(0, panel._spikeTimer - dt)
        return panel._spikeTimer > 0
    }

    /**
     * Current inrush multiplier — linearly decays from (1 + percent/100) → 1.0.
     * Returns 1.0 when no spike is active.
     */
    static spikeMultiplier(panel) {
        if (!panel._spikeTimer || panel._spikeTimer <= 0) return 1.0
        const dur  = panel.spike?.duration ?? 0.5
        const pct  = panel.spike?.percent  ?? 0
        const frac = dur > 0 ? panel._spikeTimer / dur : 0
        return 1.0 + (pct / 100) * frac
    }

    // ── Serialisation ───────────────────────────────────────────────────────

    /**
     * List of panel field names to persist in save/load.
     * Runtime state (live, blown, chargeWs …) is excluded deliberately.
     * Sub-classes extend: return [...super.configFields(), 'myField']
     * @returns {string[]}
     */
    static configFields() {
        return ['label', 'enabled']
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
        // enabled is intentionally preserved across resets (it's a user config choice)
        graph.emit(panel, null)
    }

    /**
     * Dispatch a named event to the centralised event monitor (and any other
     * window listener). Agnostic — any node can call this.
     *
     * NodeBase.dispatch(panel, 'state:change', { from: 'off', to: 'on' })
     *
     * Debounced per (panel × type) key — newest message wins.
     * Adjust NodeBase.dispatchDelay (ms) to tune throughput globally,
     * or set a static dispatchDelay on any subclass to override per node type.
     *
     * @param {Object} panel   — panel state (provides type + label)
     * @param {string} type    — dot-namespaced event name, e.g. 'state:change'
     * @param {*}      [data]  — any serialisable payload
     */
    static dispatch(panel, type, data) {
        if (panel.enabled === false) return
        const key = `${panel.id}:${type}`
        if (NodeBase._timers.has(key)) clearTimeout(NodeBase._timers.get(key))
        NodeBase._timers.set(key, setTimeout(() => {
            NodeBase._timers.delete(key)
            window.dispatchEvent(new CustomEvent('power2', {
                detail: { type, label: `${panel.type}:${panel.id}`, data }
            }))
        }, this.dispatchDelay ?? NodeBase.dispatchDelay))
    }

    /**
     * Throttle — fire immediately, then suppress further calls for dispatchDelay ms.
     * Use for continuous streaming values (temperature, voltage, etc.) where
     * debounce would suppress all events during active change.
     *
     * @param {Object} panel
     * @param {string} type
     * @param {*}      [data]
     */
    static throttle(panel, type, data) {
        if (panel.enabled === false) return
        const key = `${panel.id}:${type}`
        if (NodeBase._timers.has(key)) return  // still in cooldown, skip
        window.dispatchEvent(new CustomEvent('power2', {
            detail: { type, label: `${panel.type}:${panel.id}`, data }
        }))
        NodeBase._timers.set(key, setTimeout(() => {
            NodeBase._timers.delete(key)
        }, this.dispatchDelay ?? NodeBase.dispatchDelay))
    }

    /**
     * Called by graph.receive() when panel.enabled === false, instead of the
     * default graph.emit(panel, null) which only nulls pip 0.
     * Override in nodes that have multiple outbound pips.
     */
    static onDisabled(panel, graph) {
        graph.emit(panel, null)
    }
}

// Debounce config — change at runtime: NodeBase.dispatchDelay = 100
NodeBase.dispatchDelay = 100
NodeBase._timers       = new Map()
