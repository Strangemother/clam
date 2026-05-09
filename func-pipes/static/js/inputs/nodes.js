/*
  inputs/nodes.js
  ─────────────────────────────────────────────────────────────────────────────
  Node factories and component catalogue for the inputs system.

  Signal format: { value: number | boolean }  |  null

  Node types
  ──────────
    gamepad — reads from a browser Gamepad API device.
              No inbound pips.  One outbound pip per button/axis.
    value   — displays whatever signal arrives on its single inbound pip.
              No outbound pips (sink).

  Named pips
  ──────────
    Pips carry an optional `name` string for display.
    The DOM element id format is unchanged: ${label}-${direction}-${index}
    so the existing pipes-runtime.js wiring infrastructure works unchanged.
*/

// ── standard Gamepad API button / axis mapping ───────────────────────────────
const GAMEPAD_PIP_DEFS = [
    // Face buttons
    { index: 0,  name: 'A'      },
    { index: 1,  name: 'B'      },
    { index: 2,  name: 'X'      },
    { index: 3,  name: 'Y'      },
    // Shoulder / trigger
    { index: 4,  name: 'LB'     },
    { index: 5,  name: 'RB'     },
    { index: 6,  name: 'LT'     },
    { index: 7,  name: 'RT'     },
    // System
    { index: 8,  name: 'Select' },
    { index: 9,  name: 'Start'  },
    // Stick clicks
    { index: 10, name: 'L3'     },
    { index: 11, name: 'R3'     },
    // D-pad
    { index: 12, name: 'D↑'    },
    { index: 13, name: 'D↓'    },
    { index: 14, name: 'D←'    },
    { index: 15, name: 'D→'    },
    // Analogue axes (index 16+ avoids collision with buttons)
    { index: 16, name: 'LX'     },
    { index: 17, name: 'LY'     },
    { index: 18, name: 'RX'     },
    { index: 19, name: 'RY'     },
]

// ── component catalogue ──────────────────────────────────────────────────────
const COMPONENT_CATALOG = [
    { key: 'gamepad', group: 'Input',   type: 'gamepad', label: 'Gamepad' },
    { key: 'value',   group: 'Display', type: 'value',   label: 'Value'   },
    // Compute presets
    { key: 'compute',      group: 'Process', type: 'compute', label: 'Compute',
      inputs: [{ name: 'in', index: 0 }], outputs: [{ name: 'out', index: 0 }],
      fnSrc: 'return value' },
    { key: 'compute-xy-mag', group: 'Process', type: 'compute', label: 'XY → Magnitude',
      inputs: [{ name: 'X', index: 0 }, { name: 'Y', index: 1 }], outputs: [{ name: 'mag', index: 0 }],
      fnSrc: 'return Math.hypot(inputs.X ?? 0, inputs.Y ?? 0)' },
    { key: 'compute-xy-angle', group: 'Process', type: 'compute', label: 'XY → Angle',
      inputs: [{ name: 'X', index: 0 }, { name: 'Y', index: 1 }], outputs: [{ name: 'deg', index: 0 }],
      fnSrc: 'return Math.atan2(inputs.Y ?? 0, inputs.X ?? 0) * 180 / Math.PI' },
    { key: 'compute-clamp', group: 'Process', type: 'compute', label: 'Clamp 0–1',
      inputs: [{ name: 'in', index: 0 }], outputs: [{ name: 'out', index: 0 }],
      fnSrc: 'return Math.max(0, Math.min(1, value))' },
]

// ── factories ────────────────────────────────────────────────────────────────

function makeGamepadPanel(id, p = {}) {
    return {
        type:          'gamepad',
        label:         p.label        || 'Gamepad',
        gamepadIndex:  p.gamepadIndex ?? 0,
        state:         'idle',      // 'idle' | 'active' | 'disconnected'
        // Last-known value per pip index — used for repropagation on new connects.
        currentValues: {},
        pipsInbound:   [],
        pipsOutbound:  GAMEPAD_PIP_DEFS.map(d => ({ label: id, index: d.index, name: d.name })),
    }
}

function makeValuePanel(id, p = {}) {
    return {
        type:         'value',
        label:        p.label || 'Value',
        state:        'idle',    // 'idle' | 'active'
        value:        null,
        sources:      {},        // { [sourceId]: signal | null }
        pipsInbound:  [{ label: id, index: 0, name: 'in' }],
        pipsOutbound: [],
    }
}

function makeComputePanel(id, p = {}) {
    const inDefs  = p.inputs  || [{ name: 'in',  index: 0 }]
    const outDefs = p.outputs || [{ name: 'out', index: 0 }]
    return {
        type:         'compute',
        label:        p.label    || 'Compute',
        state:        'idle',    // 'idle' | 'active' | 'error'
        // Named pip values — keyed by pip name (e.g. { X: 0.3, Y: -0.7 })
        values:       {},
        sources:      {},
        // Gate: only run fn when a designated pip meets a condition
        gatePip:      p.gatePip    ?? null,   // pip name | null
        gateThresh:   p.gateThresh ?? 0.5,
        gateMode:     p.gateMode   ?? 'above', // 'above' | 'below' | 'nonzero' | 'always'
        // Compute function body (string, executed via new Function)
        fnSrc:        p.fnSrc      || 'return value',
        fnError:      null,
        pipsInbound:  inDefs.map(d  => ({ label: id, index: d.index ?? inDefs.indexOf(d),  name: d.name })),
        pipsOutbound: outDefs.map(d => ({ label: id, index: d.index ?? outDefs.indexOf(d), name: d.name })),
    }
}
