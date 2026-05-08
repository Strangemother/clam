/*
  power-edges.js
  ──────────────
  Edge properties for the power backbone simulation.

  Each wire connection carries optional properties that modify the signal
  as it travels from sender to receiver.

  Edge properties
  ───────────────
  {
    enabled:          bool    — false acts like a broken/cut wire (sends null)
    wireType:         string  — key from WIRE_TYPES catalog
    length:           number  — distance in pixels between the two pip elements
    manualResistance: number|null — if set, overrides the computed resistance (Ω)
  }

  Signal transformation
  ─────────────────────
  Voltage drops across wire resistance: V_out = V_in − (I × R)
  Current (amps) passes through unchanged (simplified model).
  If V_out ≤ 0, null is returned (no usable power).

  Wire type catalog
  ─────────────────
  Each type defines ohms per 100 px of pip-to-pip screen distance.
  Scale is intentionally small so short wires have negligible loss.
*/

const EdgeStore = (() => {

    // ── wire type catalog ────────────────────────────────────────────────────
    const WIRE_TYPES = [
        { key: 'copper',    label: 'Copper',     ohmsPerUnit: 0.005 },
        { key: 'aluminium', label: 'Aluminium',  ohmsPerUnit: 0.010 },
        { key: 'steel',     label: 'Steel',      ohmsPerUnit: 0.080 },
        { key: 'lossy',     label: 'Lossy Cable', ohmsPerUnit: 0.300 },
    ]

    // 1 unit = 100 px
    const PX_PER_UNIT = 100

    // ── internal store ───────────────────────────────────────────────────────
    const _store = {}  // { [connKey]: edgeProps }

    function _defaults() {
        return { enabled: true, wireType: 'copper', length: 0, manualResistance: null }
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    // Measure screen distance between two pip DOM elements.
    function calcPipDistance(senderLabel, senderDir, senderIdx, receiverLabel, receiverDir, receiverIdx) {
        const sEl = document.getElementById(`${senderLabel}-${senderDir}-${senderIdx}`)
        const rEl = document.getElementById(`${receiverLabel}-${receiverDir}-${receiverIdx}`)
        if (!sEl || !rEl) return 0
        const sr = sEl.getBoundingClientRect()
        const rr = rEl.getBoundingClientRect()
        const dx = (sr.left + sr.width  / 2) - (rr.left + rr.width  / 2)
        const dy = (sr.top  + sr.height / 2) - (rr.top  + rr.height / 2)
        return Math.round(Math.sqrt(dx * dx + dy * dy))
    }

    // Compute effective resistance in Ω for an edge.
    function computeResistance(edge) {
        if (edge.manualResistance !== null && edge.manualResistance !== undefined) {
            return edge.manualResistance
        }
        const wt = WIRE_TYPES.find(w => w.key === edge.wireType) || WIRE_TYPES[0]
        return +(edge.length / PX_PER_UNIT * wt.ohmsPerUnit).toFixed(4)
    }

    // ── public API ───────────────────────────────────────────────────────────

    // Get or create props for a connection key.
    function getOrCreate(key) {
        if (!_store[key]) _store[key] = _defaults()
        return _store[key]
    }

    function get(key) { return _store[key] || null }

    // Merge props into an existing edge entry.
    function update(key, props) {
        _store[key] = Object.assign(getOrCreate(key), props)
    }

    function remove(key) { delete _store[key] }

    // Apply edge properties to an outgoing signal.
    // Returns the transformed signal, or null if the edge is disabled / dead.
    function applyEdge(signal, key) {
        const edge = _store[key]
        if (!edge) return signal   // no entry → pristine passthrough

        if (!edge.enabled) return null

        if (!signal) return null

        const R = computeResistance(edge)
        if (R === 0) return signal

        // Voltage drop: V = I × R
        const vDrop = signal.a * R
        const vOut  = +(signal.v - vDrop).toFixed(2)
        if (vOut <= 0) return null

        return { v: vOut, a: signal.a }
    }

    // Auto-register a new connection, measuring distance from the DOM.
    // Call after the pip elements exist in the DOM.
    function register(key, obj) {
        const s = obj.sender
        const r = obj.receiver
        const dist = calcPipDistance(s.label, s.direction, s.pipIndex ?? 0,
                                     r.label, r.direction, r.pipIndex ?? 0)
        const edge = getOrCreate(key)
        edge.length = dist
        return edge
    }

    // Serialise the store for save/restore (returns plain object).
    function toJSON() {
        return JSON.parse(JSON.stringify(_store))
    }

    // Restore from a saved plain object.
    function fromJSON(data) {
        if (!data) return
        for (const key in _store) delete _store[key]
        Object.assign(_store, data)
    }

    return {
        WIRE_TYPES,
        get, getOrCreate, update, remove, register,
        computeResistance, applyEdge, calcPipDistance,
        toJSON, fromJSON,
        get store() { return _store },
    }

})()
