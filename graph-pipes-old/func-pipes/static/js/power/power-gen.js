/*
  power-gen.js
  ─────────────────────────────────────────────────────────────────────────────
  Generator control: toggle, live param changes, BFS draw computation, overload.
*/

const GenMethods = {

    toggleGen(panel) {
        if (panel.state === 'tripped') {
            // Reset a tripped generator — goes to off, user must re-enable.
            panel.overload = false
            panel.live     = false
            panel.state    = 'off'
            this._emitPower(panel, null)
            this._updateAllGenDraws()
            return
        }
        panel.live  = !panel.live
        panel.state = panel.live ? 'on' : 'off'
        this._emitPower(panel, panel.live ? { v: panel.volts, a: panel.amps } : null)
        this._updateAllGenDraws()
    },

    // Called when V or A is changed on a live gen — re-broadcast.
    genParamsChanged(panel) {
        if (panel.live && panel.state !== 'tripped') {
            // Recover from sag if params were raised
            panel.overload = false
            this._emitPower(panel, { v: panel.volts, a: panel.amps })
            this._updateAllGenDraws()
        }
    },

    /*
      _computeGenDraw — BFS from a gen's outbound pip; sums the share of
      watts this generator is responsible for at each active consuming node.

      Overload thresholds (proportion of rated amps):
        ≤ 1.0   — nominal — emit full rated signal
        1.0–1.3 — overload sag — emit voltage-sagged signal (v × 0.85)
        > 1.3   — hard overload — generator trips, emits null
    */
    _computeGenDraw(gen) {
        const visited = new Set()
        const queue   = [String(gen.id)]
        let totalW    = 0

        while (queue.length) {
            const nodeId = queue.shift()
            if (visited.has(nodeId)) continue
            visited.add(nodeId)

            const p = this.panels.find(p => String(p.id) === nodeId)
            if (!p) continue

            const shareCount = Math.max(1, Object.keys(p.powerSources || {}).length)

            if (p.type === 'bulb' && (p.state === 'on' || p.state === 'dim')) {
                totalW += p.watts / shareCount
            }
            if (p.type === 'load' && (p.state === 'on' || p.state === 'capacitor')) {
                totalW += p.watts / shareCount
            }

            ;(p.pipsOutbound || []).forEach(pip => {
                this._getOutboundConns(p, pip.index).forEach(({ inLabel }) => {
                    if (!visited.has(String(inLabel))) queue.push(String(inLabel))
                })
            })
        }

        gen.drawWatts = +totalW.toFixed(1)
        gen.drawAmps  = gen.volts > 0 ? +(totalW / gen.volts).toFixed(2) : 0

        if (!gen.live) return

        const ratio = gen.drawAmps / gen.amps

        if (ratio > 1.3) {
            // Hard trip — cut power
            if (gen.state !== 'tripped') {
                gen.overload = true
                gen.state    = 'tripped'
                this._emitPower(gen, null)
            }
        } else if (ratio > 1.0) {
            // Voltage sag — emit reduced voltage
            const sagVolts = +(gen.volts * 0.85).toFixed(1)
            gen.overload   = true
            gen.state      = 'sag'
            this._emitPower(gen, { v: sagVolts, a: gen.amps })
        } else {
            // Nominal — restore full signal if we were previously sagging
            if (gen.overload) {
                gen.overload = false
                gen.state    = 'on'
                this._emitPower(gen, { v: gen.volts, a: gen.amps })
            } else {
                gen.state = 'on'
            }
        }
    },

    _updateAllGenDraws() {
        this.panels.forEach(p => { if (p.type === 'gen') this._computeGenDraw(p) })
    },
}
