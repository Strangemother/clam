/*
  logic-nodes.js
  ──────────────
  LogicNodes — all gate operations.

  Gate method signature: (input, stored) → '0' | '1'
    input  — value arriving from the pipe (string '0' or '1')
    stored — the node's internal latched value (string '0' or '1')

  Switch and LED panels have no operation class; they are handled
  directly in logic-index.js.
*/

class LogicNodes {

    /* ── helpers ────────────────────────────────────────────────────── */

    _bool(v) {
        return v === '1' || v === 1 || v === true || v === 'true' || v === 'HIGH'
    }

    _bit(v) { return v ? '1' : '0' }

    /* ── gates ──────────────────────────────────────────────────────── */

    buffer(input)         { return this._bit(this._bool(input)) }
    not(input)            { return this._bit(!this._bool(input)) }

    and(input, stored)    { return this._bit(this._bool(input) && this._bool(stored)) }
    or(input, stored)     { return this._bit(this._bool(input) || this._bool(stored)) }
    nand(input, stored)   { return this._bit(!(this._bool(input) && this._bool(stored))) }
    nor(input, stored)    { return this._bit(!(this._bool(input) || this._bool(stored))) }
    xor(input, stored)    { return this._bit(this._bool(input) !== this._bool(stored)) }
    xnor(input, stored)   { return this._bit(this._bool(input) === this._bool(stored)) }
}

const logicNodes = new LogicNodes()

// Gate ops that need only one input (ignore stored)
const UNARY_GATES = new Set(['buffer', 'not'])

const logicGateOps = Object.getOwnPropertyNames(LogicNodes.prototype)
    .filter(n => n !== 'constructor' && !n.startsWith('_'))
    .sort()

/* ── panel factories ────────────────────────────────────────────────────── */

function makeGatePanel(id) {
    return {
        type:        'gate',
        op:          'and',
        inputs:      ['0', '0'],  // [A, B] — updated per pip
        state:       '?',
        // Two inbound pips: index 0 = A, index 1 = B
        pipsInbound: [
            { label: id, index: 0 },
            { label: id, index: 1 },
        ],
    }
}

function makeSwitchPanel(id) {
    return {
        type:   'switch',
        state:  '0',      // current switch output value
    }
}

function makeLedPanel(id) {
    return {
        type:  'led',
        state: '0',       // last received value
    }
}
