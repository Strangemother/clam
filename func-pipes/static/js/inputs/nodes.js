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
