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
        grad-voice   — calls the backend Grad Voice proxy with inbound text.
                                     Named inbound pips: 'in' and 'voice'. Named outbound pip: 'out' (event id).
    grad-voice-result — waits for a Grad Voice event to complete.
                   Named inbound pip: 'in'. Named outbound pip: 'out' (audio URL).
        grad-voice-play — submits text, waits for the audio result, and can play it.
                                     Named inbound pips: 'in' and 'voice'. Named outbound pip: 'out' (audio URL).
    text-display — sink. Renders incoming text as a message log.
                   Has a 'pass' outbound pip for chaining.
    transform    — user-defined JS function applied to text signals.
                   fn(text, name, inputs) → string | { pipName: string } | null
*/

const PROMPTING_API_BASE   = '/prompting'
const DEFAULT_ENDPOINT     = 'http://192.168.50.60:1234/api/v1/chat/'
const DEFAULT_ENDPOINT_KEY = 'lmstudio'   // must match a key in ENDPOINT_CONFIGS (prompting.py)
const DEFAULT_MODEL        = ''
const DEFAULT_GRAD_VOICE_VOICE = 'af_bella'
const DEFAULT_AUDIO_RECORD_WS = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname || 'localhost'}:8766`

// ── component catalogue ──────────────────────────────────────────────────────

const COMPONENT_CATALOG = [
    { key: 'text-input',   group: 'Input',   type: 'text-input',   label: 'Text Input'   },
    { key: 'llm',          group: 'LLM',     type: 'llm',          label: 'LLM'          },
    { key: 'audio-record', group: 'Audio',   type: 'audio-record', label: 'Mic Record'   },
    { key: 'grad-voice',   group: 'Audio',   type: 'grad-voice',   label: 'Grad Voice'   },
    { key: 'grad-voice-result', group: 'Audio', type: 'grad-voice-result', label: 'Voice Result' },
    { key: 'grad-voice-play', group: 'Audio', type: 'grad-voice-play', label: 'Speak & Play' },
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
    const outputs = Array.isArray(p.outputs) && p.outputs.length
        ? p.outputs
        : [{ name: 'out', index: 0 }]
    return {
        type:         'llm',
        label:        p.label       || 'LLM',
        state:        'idle',        // 'idle' | 'pending' | 'error'
        endpointKey:  p.endpointKey || DEFAULT_ENDPOINT_KEY,
        endpoint:     p.endpoint    || DEFAULT_ENDPOINT,  // resolved at runtime by _getLLMChat
        model:        p.model       || DEFAULT_MODEL,
        mode:        p.mode     || 'chat',     // 'chat' | 'prompt'
        templated:   p.templated ?? false,
        _manualInput: '',        // direct-test textarea
        promptPath:  p.promptPath  || '',
        promptTitle: p.promptTitle || '',
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
        pipsOutbound: outputs.map(output => ({
            label: id,
            index: output.index,
            name: output.name,
        })),
    }
}

function makeAudioRecordPanel(id, p = {}) {
    return {
        type:         'audio-record',
        label:        p.label || 'Mic Record',
        state:        'idle',
        wsUrl:        p.wsUrl || DEFAULT_AUDIO_RECORD_WS,
        filePrefix:   p.filePrefix || 'mic-record',
        messages:     [],
        lastOutput:   null,
        lastError:    null,
        lastSavedPath: '',
        lastResponse: null,
        lastSessionId: '',
        audioUrl:     '',
        recordedSeconds: 0,
        sampleRate:   0,
        _socket:      null,
        _socketToken: '',
        _expectedSocketClose: false,
        _stream:      null,
        _audioContext: null,
        _sourceNode:  null,
        _processorNode: null,
        _monitorGain: null,
        _samplesSent: 0,
        pipsInbound:  [],
        pipsOutbound: [{ label: id, index: 0, name: 'out' }],
    }
}

function makeGradVoicePanel(id, p = {}) {
    return {
        type:         'grad-voice',
        label:        p.label || 'Grad Voice',
        state:        'idle',
        voice:        p.voice || DEFAULT_GRAD_VOICE_VOICE,
        messages:     [],
        lastOutput:   null,
        lastError:    null,
        lastEventId:  '',
        lastResponse: null,
        _voiceOverride: '',
        _manualInput: '',
        _controller:  null,
        pipsInbound:  [
            { label: id, index: 0, name: 'in' },
            { label: id, index: 1, name: 'voice' },
        ],
        pipsOutbound: [{ label: id, index: 0, name: 'out' }],
    }
}

function makeGradVoiceResultPanel(id, p = {}) {
    return {
        type:         'grad-voice-result',
        label:        p.label || 'Voice Result',
        state:        'idle',
        messages:     [],
        lastOutput:   null,
        lastError:    null,
        lastEventId:  '',
        lastResponse: null,
        lastFiles:    [],
        audioUrl:     '',
        autoPlay:     p.autoPlay ?? false,
        _manualInput: '',
        _controller:  null,
        pipsInbound:  [{ label: id, index: 0, name: 'in' }],
        pipsOutbound: [{ label: id, index: 0, name: 'out' }],
    }
}

function makeGradVoicePlayPanel(id, p = {}) {
    return {
        type:         'grad-voice-play',
        label:        p.label || 'Speak & Play',
        state:        'idle',
        voice:        p.voice || DEFAULT_GRAD_VOICE_VOICE,
        lastText:     '',
        messages:     [],
        lastOutput:   null,
        lastError:    null,
        lastEventId:  '',
        lastResponse: null,
        lastFiles:    [],
        audioUrl:     '',
        autoPlay:     p.autoPlay ?? true,
        _voiceOverride: '',
        _manualInput: '',
        _controller:  null,
        pipsInbound:  [
            { label: id, index: 0, name: 'in' },
            { label: id, index: 1, name: 'voice' },
        ],
        pipsOutbound: [{ label: id, index: 0, name: 'out' }],
    }
}

function makeTextDisplayPanel(id, p = {}) {
    return {
        type:         'text-display',
        label:        p.label || 'Display',
        state:        'idle',
        latestOnly:   Boolean(p.latestOnly),
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
