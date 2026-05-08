/*
  power-tick.js
  ─────────────────────────────────────────────────────────────────────────────
  Realtime rAF tick — used exclusively for capacitor charge/drain.
*/

const TickMethods = {

    _startTick() {
        const tick = (ts) => {
            this._tickId = requestAnimationFrame(tick)
            if (!_lastTick) { _lastTick = ts; return }
            const dt = Math.min((ts - _lastTick) / 1000, 0.1)
            _lastTick = ts

            if (!this.graphRunning) return

            this.panels.forEach(p => {
                if (p.type !== 'load' || p.capacitance <= 0) return

                if (p.state === 'on') {
                    // Charge up while powered
                    p.chargeWs = Math.min(p.capacitance, p.chargeWs + p.watts * dt)
                } else if (p.state === 'capacitor') {
                    // Drain stored charge
                    p.chargeWs -= p.watts * dt
                    if (p.chargeWs <= 0) {
                        p.chargeWs = 0
                        p.state    = 'off'
                        this._emitPower(p, null)
                    }
                }
            })
        }
        this._tickId = requestAnimationFrame(tick)
    },
}
