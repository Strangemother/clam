/*
  inputs-compute.js
  ─────────────────────────────────────────────────────────────────────────────
  Compute node: named inbound/outbound pips, optional gate, user-defined
  function applied to input values on each change.

  Compute function signature (runs as an isolated function body):
    fn(value, name, inputs) → scalar | { pipName: value } | null

    value   — the new value on the pip that just changed
    name    — the pip name string (e.g. 'X')
    inputs  — object snapshot of all current inbound pip values { name: value }

    Return a scalar to emit on all outbound pips.
    Return a named object to route to specific outbound pips by name.
    Return null to emit null (signal absent) downstream.

  Gate:
    when a gate pip is configured, the compute fn only runs when that pip's
    current value satisfies the chosen mode + threshold.

  NOTE: new Function() is intentional — this is a local developer tool.
*/

const COMPUTE_PRESETS = [
    { label: 'Identity',          src: 'return value' },
    { label: 'Absolute',          src: 'return Math.abs(value)' },
    { label: 'Negate',            src: 'return -value' },
    { label: 'Sign',              src: 'return value > 0 ? 1 : value < 0 ? -1 : 0' },
    { label: 'Clamp 0–1',         src: 'return Math.max(0, Math.min(1, value))' },
    { label: 'Clamp −1–1',        src: 'return Math.max(-1, Math.min(1, value))' },
    { label: 'Square',            src: 'return value * value' },
    { label: '√ signed',          src: 'return Math.sign(value) * Math.sqrt(Math.abs(value))' },
    { label: 'Smoothstep',        src: 'return value * value * (3 - 2 * value)' },
    { label: 'Ease in-out cos',   src: 'return 0.5 - 0.5 * Math.cos(Math.PI * value)' },
    { label: 'Scale ×10',         src: 'return value * 10' },
    { label: 'Bool (≥ 0.5)',       src: 'return value >= 0.5 ? 1 : 0' },
    { label: 'XY → Magnitude',    src: 'return Math.hypot(inputs.X ?? 0, inputs.Y ?? 0)' },
    { label: 'XY → Angle (deg)',   src: 'return Math.atan2(inputs.Y ?? 0, inputs.X ?? 0) * 180 / Math.PI' },
    { label: 'XY → Normalise',    src: 'const m = Math.hypot(inputs.X??0,inputs.Y??0)||1\nreturn { X: (inputs.X??0)/m, Y: (inputs.Y??0)/m }' },
]

const ComputeMethods = {

    /* ── main processor ────────────────────────────────────────────── */

    _applyCompute(panel, changedPipName) {
        if (!changedPipName) return

        // Gate check — skip execution if gate condition not met
        if (panel.gatePip) {
            const gv   = panel.values[panel.gatePip] ?? 0
            const pass = panel.gateMode === 'above'   ? gv >= panel.gateThresh
                       : panel.gateMode === 'below'   ? gv <= panel.gateThresh
                       : panel.gateMode === 'nonzero' ? gv !== 0
                       : true  // 'always'
            if (!pass) return
        }

        panel.fnError = null
        const inputs  = { ...panel.values }   // snapshot — all named pip values
        const value   = inputs[changedPipName] ?? null

        let result
        try {
            // eslint-disable-next-line no-new-func
            result = new Function('value', 'name', 'inputs', panel.fnSrc)(value, changedPipName, inputs)
        } catch (e) {
            panel.fnError = e.message
            panel.state   = 'error'
            return
        }

        panel.state = 'active'
        this._emitComputeResult(panel, result)
    },

    _emitComputeResult(panel, result) {
        if (result === null || result === undefined) {
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
            return
        }
        // Named object return — route per outbound pip name
        if (typeof result === 'object' && !Array.isArray(result)) {
            panel.pipsOutbound.forEach(pip => {
                if (pip.name in result) {
                    this._emitFromPip(panel, pip.index, { value: result[pip.name] })
                }
            })
        } else {
            // Scalar/boolean — broadcast on all outbound pips
            panel.pipsOutbound.forEach(pip => {
                this._emitFromPip(panel, pip.index, { value: result })
            })
        }
    },

    // Re-run the fn with the most recently changed pip that has a value.
    _rerunCompute(panel) {
        const pip = panel.pipsInbound.find(p => panel.values[p.name] !== undefined)
        if (pip) this._applyCompute(panel, pip.name)
    },

    // Apply a preset src string and immediately re-evaluate.
    setComputePreset(panel, src) {
        if (!src) return
        panel.fnSrc   = src
        panel.fnError = null
        this._rerunCompute(panel)
    },

    /* ── pip management ─────────────────────────────────────────────── */

    addInboundPip(panel) {
        const idx  = panel.pipsInbound.length
        panel.pipsInbound.push({ label: panel.id, index: idx, name: `in${idx}` })
    },

    removeInboundPip(panel, pipIndex) {
        const pip = panel.pipsInbound.find(p => p.index === pipIndex)
        if (!pip) return
        delete panel.values[pip.name]
        // If this was the gate pip, clear the gate
        if (panel.gatePip === pip.name) panel.gatePip = null
        panel.pipsInbound = panel.pipsInbound.filter(p => p.index !== pipIndex)
    },

    addOutboundPip(panel) {
        const idx = panel.pipsOutbound.length
        panel.pipsOutbound.push({ label: panel.id, index: idx, name: `out${idx}` })
    },

    removeOutboundPip(panel, pipIndex) {
        this._emitFromPip(panel, pipIndex, null)   // clear any wired downstream
        panel.pipsOutbound = panel.pipsOutbound.filter(p => p.index !== pipIndex)
    },
}
