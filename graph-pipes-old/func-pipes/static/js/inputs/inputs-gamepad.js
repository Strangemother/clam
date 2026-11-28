/*
  inputs-gamepad.js
  ─────────────────────────────────────────────────────────────────────────────
  Gamepad node: Gamepad API polling via rAF, per-pip emit on value change.

  Each gamepad panel polls navigator.getGamepads()[panel.gamepadIndex] every
  animation frame and emits { value } signals only when a button or axis
  value changes — avoiding unnecessary downstream churn.

  Button press values:    0.0 (released) … 1.0 (fully pressed)
  Axis values:           -1.0 … 1.0
*/

const GamepadMethods = {

    /* ── rAF poll loop ─────────────────────────────────────────────── */

    _startGamepadPoll() {
        let prev = {}   // { panelId: { pipIndex: lastValue } }

        const poll = () => {
            this._pollId = requestAnimationFrame(poll)

            const gamepads = navigator.getGamepads?.() ?? []
            this.panels.forEach(p => {
                if (p.type !== 'gamepad') return

                const gp = gamepads[p.gamepadIndex]
                if (!gp || !gp.connected) {
                    if (p.state !== 'idle') {
                        p.state = 'idle'
                        p.pipsOutbound.forEach(pip => this._emitFromPip(p, pip.index, null))
                        prev[p.id] = {}
                    }
                    return
                }

                p.state = 'active'
                if (!prev[p.id]) prev[p.id] = {}

                // Buttons (pips 0–15)
                gp.buttons.forEach((btn, i) => {
                    if (i >= 16) return
                    const v = +btn.value.toFixed(4)
                    if (prev[p.id][i] !== v) {
                        prev[p.id][i]       = v
                        p.currentValues[i]  = v
                        this._emitFromPip(p, i, { value: v })
                    }
                })

                // Axes (pips 16–19)
                gp.axes.forEach((ax, i) => {
                    const pipIdx = 16 + i
                    const v = +ax.toFixed(4)
                    if (prev[p.id][pipIdx] !== v) {
                        prev[p.id][pipIdx]      = v
                        p.currentValues[pipIdx] = v
                        this._emitFromPip(p, pipIdx, { value: v })
                    }
                })
            })
        }

        this._pollId = requestAnimationFrame(poll)
    },

    /* ── gamepad index control ─────────────────────────────────────── */

    gamepadIndexChanged(panel) {
        // Reset current values so the new index starts fresh
        panel.currentValues = {}
        panel.state = 'idle'
        panel.pipsOutbound.forEach(pip => this._emitFromPip(panel, pip.index, null))
    },
}
