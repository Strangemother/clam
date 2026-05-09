/*
  prompting/nodes.js
  ─────────────────────────────────────────────────────────────────────────────
  Node factories and component catalogue for the prompting system.

  Signal format: { text: string, meta?: {} }  |  null

    text   — the primary string payload (message, response, transformed text…)
    meta   — optional metadata: { role, model, promptPath, … }
    null   — signal absent / upstream disconnected

  Node types
  ──────────
    text-input   — user-typed text entry. Sends { text } downstream.
                   Can also receive from upstream and forward (pass-through).
    llm          — calls an LLM via the Chat class.
                   Named inbound pips: 'in' (message), 'system' (prompt override).
                   Named outbound pip: 'out' (response text).
    text-display — sink. Renders incoming text as a message log.
                   Has a 'pass' outbound pip for chaining.
    transform    — user-defined JS function applied to text signals.
                   fn(text, name, inputs) → string | { pipName: string } | null
*/

const PROMPTING_API_BASE = '/prompting'
const DEFAULT_ENDPOINT   = 'http://192.168.50.60:1234/api/v1/chat/'
const DEFAULT_MODEL      = ''

// ── component catalogue ──────────────────────────────────────────────────────

const COMPONENT_CATALOG = [
    { key: 'text-input',   group: 'Input',   type: 'text-input',   label: 'Text Input'   },
    { key: 'llm',          group: 'LLM',     type: 'llm',          label: 'LLM'          },
    { key: 'text-display', group: 'Display', type: 'text-display', label: 'Text Display' },
    { key: 'transform',    group: 'Process', type: 'transform',    label: 'Transform'    },

    { key: 'delay',          group: 'Flow',    type: 'delay',        label: 'Delay'        },
    { key: 'pyfunc',         group: 'Flow',    type: 'pyfunc',       label: 'Python Func'  },
    { key: 'event-input',    group: 'Input',   type: 'event-input',  label: 'Event Input'  },

    // Transform presets
    { key: 'transform-upper',
      group: 'Process', type: 'transform', label: 'Uppercase',
      inputs: [{ name: 'in', index: 0 }], outputs: [{ name: 'out', index: 0 }],
      fnSrc: 'return text.toUpperCase()' },
    { key: 'transform-trim',
      group: 'Process', type: 'transform', label: 'Trim',
      inputs: [{ name: 'in', index: 0 }], outputs: [{ name: 'out', index: 0 }],
      fnSrc: 'return text.trim()' },
    { key: 'transform-first-line',
      group: 'Process', type: 'transform', label: 'First Line',
      inputs: [{ name: 'in', index: 0 }], outputs: [{ name: 'out', index: 0 }],
      fnSrc: 'return text.split("\\n")[0].trim()' },
    { key: 'transform-json-text',
      group: 'Process', type: 'transform', label: 'JSON → text',
      inputs: [{ name: 'in', index: 0 }], outputs: [{ name: 'out', index: 0 }],
      fnSrc: 'try { const o = JSON.parse(text); return o.text ?? o.content ?? o.message ?? text } catch(e) { return text }' },
    { key: 'transform-prefix',
      group: 'Process', type: 'transform', label: 'Prepend prefix pip',
      inputs: [{ name: 'text', index: 0 }, { name: 'prefix', index: 1 }],
      outputs: [{ name: 'out', index: 0 }],
      fnSrc: 'return (inputs.prefix ? inputs.prefix + "\\n" : "") + text' },
]

// ── factories ────────────────────────────────────────────────────────────────

function makeTextInputPanel(id, p = {}) {
    return {
        type:         'text-input',
        label:        p.label || 'Text Input',
        state:        'idle',
        input:        '',
        messages:     [],        // display log [{ role, text }]
        lastOutput:   null,      // last emitted signal, for repropagation
        pipsInbound:  [],        // can receive from upstream (pass-through)
        pipsOutbound: [{ label: id, index: 0, name: 'out' }],
    }
}

function makeLLMPanel(id, p = {}) {
    return {
        type:        'llm',
        label:       p.label    || 'LLM',
        state:       'idle',     // 'idle' | 'pending' | 'error'
        endpoint:    p.endpoint || DEFAULT_ENDPOINT,
        model:       p.model    || DEFAULT_MODEL,
        mode:        p.mode     || 'chat',     // 'chat' | 'prompt'
        templated:   p.templated ?? false,
        _manualInput: '',        // direct-test textarea
        prompt:      null,       // { path, content, title } — loaded system prompt
        description: '',
        showPrompt:  false,
        messages:    [],         // display log [{ role, content }]
        lastOutput:  null,       // last emitted signal
        _chat:       null,       // Chat instance (managed by LLMMethods)
        pipsInbound: [
            { label: id, index: 0, name: 'in'     },  // message input
            { label: id, index: 1, name: 'system' },  // system-prompt override
        ],
        pipsOutbound: [{ label: id, index: 0, name: 'out' }],
    }
}

function makeTextDisplayPanel(id, p = {}) {
    return {
        type:         'text-display',
        label:        p.label || 'Display',
        state:        'idle',
        messages:     [],        // displayed history [{ role, text }]
        sources:      {},
        pipsInbound:  [{ label: id, index: 0, name: 'in'   }],
        pipsOutbound: [{ label: id, index: 0, name: 'pass' }],
    }
}

function makePyFuncPanel(id, p = {}) {
    return {
        type:         'pyfunc',
        label:        p.label || 'Python Func',
        state:        'idle',    // 'idle' | 'running' | 'error'
        fnName:       null,      // selected function name string
        values:       {},        // { paramName: string } — current inbound values
        lastOutput:   null,      // last { text, meta } signal emitted
        lastError:    null,      // last error string, or null
        autoCall:     false,     // call automatically when all required pips have values
        pipsInbound:  [],        // rebuilt when a function is selected
        pipsOutbound: [{ label: id, index: 0, name: 'result' }],
    }
}

function makeEventInputPanel(id, p = {}) {
    const outputs = p.outputs || [{ name: 'out', index: 0 }]
    return {
        type:          'event-input',
        label:         p.label     || 'Event Input',
        state:         'idle',                         // 'idle' | 'active'
        eventName:     p.eventName || 'graph:input',   // DOM event name to listen for
        lastDetail:    null,                           // raw detail of last fired event
        lastReceived:  null,                           // time string of last event
        _listener:     null,                           // runtime only — not serialised
        pipsInbound:   [],
        pipsOutbound:  outputs.map(o => ({ label: id, index: o.index, name: o.name })),
    }
}

function makeDelayPanel(id, p = {}) {
    return {
        type:         'delay',
        label:        p.label || 'Delay',
        state:        'idle',    // 'idle' | 'waiting' | 'paused'
        delayMs:      p.delayMs ?? 1000,  // milliseconds to wait before forwarding
        paused:       false,              // when true, hold queue until released
        queue:        [],                 // [{ signal, timerId }] pending signals
        pipsInbound:  [{ label: id, index: 0, name: 'in'  }],
        pipsOutbound: [{ label: id, index: 0, name: 'out' }],
    }
}

function makeTransformPanel(id, p = {}) {
    const inputs  = p.inputs  || [{ name: 'in',  index: 0 }]
    const outputs = p.outputs || [{ name: 'out', index: 0 }]
    return {
        type:         'transform',
        label:        p.label      || 'Transform',
        state:        'idle',
        values:       {},          // pipName → string value
        fnSrc:        p.fnSrc     || 'return text',
        fnError:      null,
        gatePip:      p.gatePip   || null,
        gateMode:     p.gateMode  || 'truthy', // 'truthy'|'always'|'matches'
        gatePattern:  p.gatePattern || '',     // regex string for 'matches' mode
        pipsInbound:  inputs.map(inp  => ({ label: id, index: inp.index, name: inp.name })),
        pipsOutbound: outputs.map(out => ({ label: id, index: out.index, name: out.name })),
    }
}
