/*
  exec-nodes.js
  ─────────────
  ExecNodes is a plain class whose methods are the available graph transforms.
  Each method receives a single string (the pipe value) and returns a string
  (or a Promise<string>).  That's the full contract — nothing else required.

  Add new transforms by adding new methods.  They appear automatically in the
  node dropdown.
*/

class ExecNodes {

    /* ── text transforms ─────────────────────────────────────────────── */

    passthrough(input) {
        return input
    }

    uppercase(input) {
        return input.toUpperCase()
    }

    lowercase(input) {
        return input.toLowerCase()
    }

    trim(input) {
        return input.trim()
    }

    reverse(input) {
        return [...input].reverse().join('')
    }

    /* ── analysis ────────────────────────────────────────────────────── */

    wordCount(input) {
        const n = input.trim().split(/\s+/).filter(Boolean).length
        return String(n)
    }

    charCount(input) {
        return String(input.length)
    }

    lineCount(input) {
        return String(input.split('\n').length)
    }

    /* ── format ──────────────────────────────────────────────────────── */

    jsonFormat(input) {
        try {
            return JSON.stringify(JSON.parse(input), null, 2)
        } catch {
            return input
        }
    }

    csvToLines(input) {
        return input.split(',').map(s => s.trim()).join('\n')
    }

    linesToCsv(input) {
        return input.split('\n').map(s => s.trim()).filter(Boolean).join(', ')
    }

}

/*
  Expose a single shared instance and a sorted list of method names.
  Downstream: execNodes.run(name, input) handles safe dispatch.
*/
const execNodes = new ExecNodes()

const execNodeNames = Object.getOwnPropertyNames(ExecNodes.prototype)
    .filter(n => n !== 'constructor')
    .sort()
