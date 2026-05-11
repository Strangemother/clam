/*
  core/edge-store.js
  ─────────────────────────────────────────────────────────────────────────────
  EdgeStore — per-wire properties and signal transformation.

  Identical in purpose to power/power-edges.js but kept as a clean, isolated
  module so the power-2 system has no dependency on power-1 files.

  Wire properties
  ───────────────
  {
    enabled:          bool        — false = broken wire (passes null)
    wireType:         string      — key from WIRE_TYPES catalog
    length:           number      — pip-to-pip distance in screen pixels
    manualResistance: number|null — overrides computed resistance when set
  }

  Signal transformation
  ─────────────────────
  R (Ω) = (length / PX_PER_UNIT) × ohmsPerUnit
  V_out = V_in − (I × R)           ← resistive voltage drop
  A_out = A_in                     ← amps pass through unchanged

  If V_out ≤ 0 the function returns null (wire too resistive for the load).

  Worked example
  ──────────────
  Wire: copper (0.005 Ω/unit), 300 px long, carrying 10 A at 240 V

    R      = (300 / 100) × 0.005  = 0.015 Ω
    V_drop = 10 A × 0.015 Ω      = 0.15 V
    V_out  = 240 − 0.15           = 239.85 V
    A_out  = 10 A  (unchanged)

  With lossy cable (0.300 Ω/unit) over the same 300 px at 10 A:

    R      = 3 × 0.300            = 0.900 Ω
    V_drop = 10 × 0.900           = 9.0 V
    V_out  = 240 − 9.0            = 231.0 V

  PX_PER_UNIT = 100, so every 100 pixels of wire length equals one resistance unit.
*/

const EdgeStore2 = (() => {

    // ── Wire type catalog ────────────────────────────────────────────────────
    const WIRE_TYPES = [
        { key: 'copper',    label: 'Copper',      ohmsPerUnit: 0.005, color: '#00e87c' },
        { key: 'aluminium', label: 'Aluminium',   ohmsPerUnit: 0.010, color: '#aadd00' },
        { key: 'steel',     label: 'Steel',       ohmsPerUnit: 0.080, color: '#ff9900' },
        { key: 'lossy',     label: 'Lossy Cable', ohmsPerUnit: 0.300, color: '#ff3333' },
    ]

    const PX_PER_UNIT = 100   // 1 resistance unit = 100 pixels

    // ── Internal store ────────────────────────────────────────────────────────
    const _store = {}   // { [connKey]: edgeProps }

    function _defaults() {
        return { enabled: true, wireType: 'copper', length: 0, manualResistance: null }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** Measure screen distance between two pip DOM elements. */
    function calcPipDistance(senderLabel, senderDir, senderIdx,
                             receiverLabel, receiverDir, receiverIdx) {
        const sEl = document.getElementById(`${senderLabel}-${senderDir}-${senderIdx}`)
        const rEl = document.getElementById(`${receiverLabel}-${receiverDir}-${receiverIdx}`)
        if (!sEl || !rEl) return 0
        const sr = sEl.getBoundingClientRect()
        const rr = rEl.getBoundingClientRect()
        const dx = (sr.left + sr.width  / 2) - (rr.left + rr.width  / 2)
        const dy = (sr.top  + sr.height / 2) - (rr.top  + rr.height / 2)
        return Math.round(Math.sqrt(dx * dx + dy * dy))
    }

    /** Effective wire resistance in Ω. */
    function computeResistance(edge) {
        if (edge.manualResistance !== null && edge.manualResistance !== undefined) {
            return edge.manualResistance
        }
        const wt = WIRE_TYPES.find(w => w.key === edge.wireType) || WIRE_TYPES[0]
        return +(edge.length / PX_PER_UNIT * wt.ohmsPerUnit).toFixed(4)
    }

    // ── Public API ────────────────────────────────────────────────────────────

    function getOrCreate(key) {
        if (!_store[key]) _store[key] = _defaults()
        return _store[key]
    }

    function get(key) { return _store[key] || null }

    function update(key, props) {
        _store[key] = Object.assign(getOrCreate(key), props)
    }

    function remove(key) { delete _store[key] }

    /** Transform a signal through this edge (resistance drop, enable/disable). */
    function applyEdge(signal, key) {
        const edge = _store[key]
        if (!edge) return signal          // no entry → pristine passthrough
        if (!edge.enabled) return null
        if (!signal) return null

        const R = computeResistance(edge)
        if (R === 0) return signal

        const vDrop = signal.a * R
        const vOut  = +(signal.v - vDrop).toFixed(2)
        if (vOut <= 0) return null

        return { v: vOut, a: signal.a }
    }

    /**
     * Auto-register a new connection from the DOM pip elements.
     * Call after the pip elements have been added to the DOM.
     */
    function register(key, obj) {
        const s = obj.sender
        const r = obj.receiver
        const dist = calcPipDistance(
            s.label, s.direction, s.pipIndex ?? 0,
            r.label, r.direction, r.pipIndex ?? 0
        )
        const edge = getOrCreate(key)
        edge.length = dist
        return edge
    }

    /** Canvas line color reflecting wire type and enabled state. */
    function colorForEdge(key) {
        const edge = _store[key]
        if (edge?.enabled === false) return '#ff333366'
        const typeKey = edge?.wireType ?? 'copper'
        const wt = WIRE_TYPES.find(w => w.key === typeKey) || WIRE_TYPES[0]
        return wt.color
    }

    function toJSON()        { return JSON.parse(JSON.stringify(_store)) }
    function fromJSON(data)  {
        if (!data) return
        for (const key in _store) delete _store[key]
        Object.assign(_store, data)
    }

    return {
        WIRE_TYPES,
        get, getOrCreate, update, remove, register,
        computeResistance, applyEdge, calcPipDistance, colorForEdge,
        toJSON, fromJSON,
        get store() { return _store },
    }

})()
