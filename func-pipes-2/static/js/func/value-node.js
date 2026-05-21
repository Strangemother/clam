/*
  value-node.js
  ─────────────
  A stateful node type. It holds an internal value that persists between calls.

  On each invocation:
    result = combine(input, internalValue)
    internalValue = result          ← stored for the next call
    output result downstream

  Available combine operations are declared on the class so they auto-populate
  the UI dropdown, following the same pattern as ExecNodes.
*/

class ValueNode {

    /* ── combine operations ────────────────────────────────────────────
       Each method receives (input, stored) and returns a string result.
    ── */

    append(input, stored)  { return stored + input }
    prepend(input, stored) { return input + stored }
    replace(input, stored) { return input }         // input replaces stored
    add(input, stored)     {
        const a = parseFloat(stored) || 0
        const b = parseFloat(input)  || 0
        return String(a + b)
    }
    multiply(input, stored) {
        const a = parseFloat(stored) || 0
        const b = parseFloat(input)  || 0
        return String(a * b)
    }
    joinLines(input, stored) {
        return [stored, input].filter(Boolean).join('\n')
    }
    joinCsv(input, stored) {
        return [stored, input].filter(Boolean).join(', ')
    }
    max(input, stored) {
        return String(Math.max(parseFloat(stored) || 0, parseFloat(input) || 0))
    }
    min(input, stored) {
        return String(Math.min(parseFloat(stored) || 0, parseFloat(input) || 0))
    }
}

const valueNode = new ValueNode()

const valueNodeOps = Object.getOwnPropertyNames(ValueNode.prototype)
    .filter(n => n !== 'constructor')

/*
  makeValuePanel() — factory for a panel of type 'value'.
  Returns a plain object; merged into the panel by index.js.
*/
function makeValuePanel(id) {
    return {
        type:      'value',
        op:        'append',   // selected combine operation
        stored:    '',         // the persistent internal value
    }
}
