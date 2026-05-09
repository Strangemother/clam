/*
  prompt-transform.js
  ─────────────────────────────────────────────────────────────────────────────
  Transform node — the text-domain equivalent of the inputs ComputeNode.

  Compute function signature (runs as an isolated function body):
    fn(text, name, inputs) → string | { pipName: string } | null

    text    — the incoming string on the pip that just changed
    name    — the pip name string (e.g. 'in')
    inputs  — snapshot of all named inbound pip values { name: string }

    Return a string   → emit on all outbound pips.
    Return an object  → route each value to the outbound pip with matching name.
    Return null       → emit null (signal absent) downstream.

  Gate:
    'truthy'  — run only if the incoming text is non-empty
    'always'  — always run (even on empty string)
    'matches' — run only if any input value matches gatePattern (regex string)

  NOTE: new Function() is intentional — this is a local developer tool.
*/

const TRANSFORM_PRESETS = [
    { label: 'Pass-through',        src: 'return text' },
    { label: 'Uppercase',           src: 'return text.toUpperCase()' },
    { label: 'Lowercase',           src: 'return text.toLowerCase()' },
    { label: 'Trim whitespace',     src: 'return text.trim()' },
    { label: 'First line only',     src: 'return text.split("\\n")[0].trim()' },
    { label: 'Last line only',      src: 'const ls = text.split("\\n").filter(l=>l.trim()); return ls[ls.length-1] ?? ""' },
    { label: 'Word count → text',   src: 'return String(text.trim().split(/\\s+/).filter(Boolean).length)' },
    { label: 'Char count → text',   src: 'return String(text.length)' },
    { label: 'JSON → text field',   src: 'try { const o = JSON.parse(text); return o.text ?? o.content ?? o.message ?? text } catch(e) { return text }' },
    { label: 'Wrap in quotes',      src: 'return `"${text.replace(/"/g, "\\\\\"")}"` ' },
    { label: 'Prepend prefix pip',  src: 'return (inputs.prefix ? inputs.prefix + "\\n" : "") + text' },
    { label: 'Append suffix pip',   src: 'return text + (inputs.suffix ? "\\n" + inputs.suffix : "")' },
    { label: 'Template {{text}}',   src: 'return (inputs.template || "{text}").replace("{text}", text)' },
    { label: 'Extract JSON value',  src: '// Set key=<fieldname> in another pip\ntry { const o=JSON.parse(text); return String(o[inputs.key] ?? "") } catch(e) { return "" }' },
    { label: 'Regex replace',       src: '// Set pattern and replacement as separate pips\nreturn text.replace(new RegExp(inputs.pattern||"","g"), inputs.replacement||"")' },
]

const TransformMethods = {

    /* ── main processor — called by prompt-signal.js ─────────────────── */

    _applyTransform(panel, changedPipName) {
        if (!changedPipName) return

        // Gate check
        const fail = this._transformGateFails(panel)
        if (fail) return

        panel.fnError = null
        const inputs  = { ...panel.values }
        const text    = inputs[changedPipName] ?? ''

        let result
        try {
            // eslint-disable-next-line no-new-func
            result = new Function('text', 'name', 'inputs', panel.fnSrc)(text, changedPipName, inputs)
        } catch (e) {
            panel.fnError = e.message
            panel.state   = 'error'
            return
        }

        panel.state = 'active'
        this._emitTransformResult(panel, result)
    },

    _transformGateFails(panel) {
        if (!panel.gatePip) return false
        const gv = panel.values[panel.gatePip] ?? ''
        if (panel.gateMode === 'truthy')  return !gv
        if (panel.gateMode === 'always')  return false
        if (panel.gateMode === 'matches') {
            try { return !new RegExp(panel.gatePattern || '').test(gv) } catch { return true }
        }
        return false
    },

    _emitTransformResult(panel, result) {
        if (result === null || result === undefined) {
            panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
            return
        }
        // Named object — route per outbound pip name
        if (typeof result === 'object' && !Array.isArray(result)) {
            panel.pipsOutbound.forEach(pip => {
                if (pip.name in result) {
                    const text = result[pip.name]
                    this._emitFromPip(panel, pip.index, text != null ? { text: String(text) } : null)
                }
            })
        } else {
            // Scalar string → broadcast
            const text = String(result)
            panel.pipsOutbound.forEach(pip => {
                this._emitFromPip(panel, pip.index, { text })
            })
        }
    },

    _rerunTransform(panel) {
        const pip = panel.pipsInbound.find(p => panel.values[p.name] !== undefined)
        if (pip) this._applyTransform(panel, pip.name)
    },

    setTransformPreset(panel, src) {
        if (!src) return
        panel.fnSrc   = src
        panel.fnError = null
        this._rerunTransform(panel)
    },

    /* ── pip management ─────────────────────────────────────────────── */

    addInboundPip(panel) {
        const idx = panel.pipsInbound.length
        panel.pipsInbound.push({ label: panel.id, index: idx, name: `in${idx}` })
    },

    removeInboundPip(panel, pipIndex) {
        const pip = panel.pipsInbound.find(p => p.index === pipIndex)
        if (!pip) return
        delete panel.values[pip.name]
        panel.pipsInbound = panel.pipsInbound.filter(p => p.index !== pipIndex)
    },

    addOutboundPip(panel) {
        const idx = panel.pipsOutbound.length
        panel.pipsOutbound.push({ label: panel.id, index: idx, name: `out${idx}` })
    },

    removeOutboundPip(panel, pipIndex) {
        this._emitFromPip(panel, pipIndex, null)
        panel.pipsOutbound = panel.pipsOutbound.filter(p => p.index !== pipIndex)
    },
}
