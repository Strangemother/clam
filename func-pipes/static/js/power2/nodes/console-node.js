/*
  nodes/console-node.js — Console / Computer Terminal
  ─────────────────────────────────────────────────────────────────────────────
  Extends Load with a boot simulation: when power is applied the console
  takes time to boot before becoming 'ready', and shuts down gracefully
  when power is removed. The capacitor buffer (if configured) allows a
  clean shutdown window after power loss.

  This class demonstrates:
    • Extending Load for a specialised equipment type.
    • Using tick() to drive a multi-stage state machine (boot/ready/shutdown).
    • Adding new display state fields while reusing all Load power logic.

  Extra state
  ───────────
  bootState        string  — 'off' | 'booting' | 'ready' | 'shutdown'
  bootProgress     number  — 0–100 (% through the boot sequence)
  bootDuration     number  — seconds to fully boot (default 5)
  shutdownDuration number  — seconds to gracefully shutdown (default 2)
  _effectiveWatts  number  — current actual draw (ramps with boot, oscillates ±10% at ready)
  _loadAccum       number  — time accumulator driving idle power fluctuation

  Power draw model
  ────────────────
  booting  — ramps from 0 → watts proportional to bootProgress
  ready    — oscillates between ~90–100% of rated watts (slow sine, ±10%)
  shutdown — ramps from current draw back down to 0
  off      — 0 W

  Power/capacitor logic inherited from Load.
  States: inherited from Load ('off' | 'on' | 'brownout' | 'capacitor' | 'blown')
*/

class ConsoleNode extends Load {

    static type  = 'console'
    static label = 'Console'
    static group = 'Equipment'

    static _defaultSpike() {
        return { enabled: true, percent: 4, duration: 2.0 }
    }

    static catalog = [
        { key: 'console-sm',  label: 'Console (SM)',  watts: 30,  minVolts: 180, capacitance: 10 },
        { key: 'console-lg',  label: 'Console (LG)',  watts: 80,  minVolts: 180, capacitance: 20 },
        { key: 'server-rack', label: 'Server Rack',   watts: 500, minVolts: 200, capacitance: 50 },
        { key: 'workstation', label: 'Workstation',   watts: 250, minVolts: 190, capacitance: 30 },
    ]

    static defaults(id, preset = {}) {
        return {
            ...super.defaults(id, preset),
            label:           preset.label || 'Console',
            watts:           preset.watts    ?? 50,
            minVolts:        preset.minVolts ?? 180,
            capacitance:     preset.capacitance ?? 20,
            // Boot simulation
            bootState:        'off',   // 'off' | 'booting' | 'ready' | 'shutdown'
            bootProgress:     0,       // 0–100
            bootDuration:     preset.bootDuration     ?? 5,
            shutdownDuration: preset.shutdownDuration ?? 2,
            _shutdownTimer:   0,
            // Dynamic power draw
            _effectiveWatts:  0,
            _loadAccum:       0,
            spike:            preset.spike ? { ...preset.spike } : { ...this._defaultSpike() },
        }
    }

    static configFields() {
        return [...super.configFields(), 'bootDuration', 'shutdownDuration', 'spike']
    }

    /**
     * Swap in the dynamic draw, delegate to Load.apply(), then restore rated watts.
     * During the inrush spike the full rated watts (× multiplier) is used instead of
     * _effectiveWatts so the upstream sees a realistic startup burst.
     */
    static apply(panel, signal, graph) {
        const rated  = panel.watts
        const m      = NodeBase.spikeMultiplier(panel)
        panel.watts  = m > 1.0 ? rated * m : (panel._effectiveWatts ?? 0)
        super.apply(panel, signal, graph)
        panel.watts  = rated
    }

    static tick(panel, dt, graph) {
        // Capacitor drain / charge from Load (uses _effectiveWatts via apply swap)
        super.tick(panel, dt, graph)

        const powered  = panel.state === 'on' || panel.state === 'capacitor'
        const prevBoot = panel.bootState

        if (powered && panel.bootState !== 'ready') {
            if (panel.bootState !== 'booting') {
                panel.bootState    = 'booting'
                panel.bootProgress = 0
                NodeBase.startSpike(panel)   // inrush burst at the moment boot begins
            }
            const rate = 100 / Math.max(0.1, panel.bootDuration)
            panel.bootProgress = Math.min(100, panel.bootProgress + rate * dt)
            if (panel.bootProgress >= 100) panel.bootState = 'ready'
        } else if (!powered && panel.bootState !== 'off') {
            if (panel.bootState !== 'shutdown') {
                panel.bootState      = 'shutdown'
                panel._shutdownTimer = 0
            }
            panel._shutdownTimer += dt
            const pct = Math.min(100, (panel._shutdownTimer / Math.max(0.1, panel.shutdownDuration)) * 100)
            panel.bootProgress = 100 - pct
            if (panel._shutdownTimer >= panel.shutdownDuration) {
                panel.bootState    = 'off'
                panel.bootProgress = 0
            }
        }

        // ── Dynamic power draw ──────────────────────────────────────────────
        panel._loadAccum += dt
        const rated = panel.watts

        if (panel.bootState === 'off') {
            panel._effectiveWatts = 0
        } else if (panel.bootState === 'booting') {
            // Ramp from 0 → rated proportional to boot progress
            const ramp = panel.bootProgress / 100
            panel._effectiveWatts = rated * ramp
        } else if (panel.bootState === 'ready') {
            // Oscillate ±10% around 90% of rated (slow sine, ~20 s period)
            const sine = Math.sin(panel._loadAccum * 0.314)  // 2π / 20s ≈ 0.314
            panel._effectiveWatts = rated * (0.9 + 0.1 * sine)
        } else if (panel.bootState === 'shutdown') {
            // Ramp back down as shutdown progresses
            const remaining = panel.bootProgress / 100   // bootProgress counts down during shutdown
            panel._effectiveWatts = rated * remaining * 0.9
        }

        // Expose to graph.computeGenDraw() via the currentWatts convention
        panel.currentWatts = panel._effectiveWatts

        if (panel.bootState !== prevBoot)
            ConsoleNode.dispatch(panel, 'console:boot-state', { from: prevBoot, to: panel.bootState })

        if (panel.bootState === 'booting' || panel.bootState === 'shutdown') {
            const pct = +panel.bootProgress.toFixed(0)
            if (pct !== panel._lastBootPct) {
                panel._lastBootPct = pct
                ConsoleNode.throttle(panel, 'console:boot-progress', { bootState: panel.bootState, progress: pct })
            }
        }
    }

    static reset(panel, graph) {
        panel.bootState       = 'off'
        panel.bootProgress    = 0
        panel._shutdownTimer  = 0
        panel._lastBootPct    = null
        panel._effectiveWatts = 0
        panel._loadAccum      = 0
        panel.currentWatts    = 0
        ConsoleNode.dispatch(panel, 'console:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(ConsoleNode)
