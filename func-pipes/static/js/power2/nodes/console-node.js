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
  bootState    string  — 'off' | 'booting' | 'ready' | 'shutdown'
  bootProgress number  — 0–100 (% through the boot sequence)
  bootDuration number  — seconds to fully boot (default 5)
  shutdownDuration number — seconds to gracefully shutdown (default 2)

  Power/capacitor logic inherited from Load.
  States: inherited from Load ('off' | 'on' | 'brownout' | 'capacitor' | 'blown')
*/

class ConsoleNode extends Load {

    static type  = 'console'
    static label = 'Console'
    static group = 'Equipment'

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
            bootState:       'off',   // 'off' | 'booting' | 'ready' | 'shutdown'
            bootProgress:    0,       // 0–100
            bootDuration:    preset.bootDuration    ?? 5,
            shutdownDuration: preset.shutdownDuration ?? 2,
            _shutdownTimer:  0,
        }
    }

    static configFields() {
        return [...super.configFields(), 'bootDuration', 'shutdownDuration']
    }

    static tick(panel, dt, graph) {
        // Capacitor drain / charge from Load
        super.tick(panel, dt, graph)

        const powered  = panel.state === 'on' || panel.state === 'capacitor'
        const prevBoot = panel.bootState

        if (powered && panel.bootState !== 'ready') {
            if (panel.bootState !== 'booting') {
                panel.bootState    = 'booting'
                panel.bootProgress = 0
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
        panel.bootState      = 'off'
        panel.bootProgress   = 0
        panel._shutdownTimer = 0
        panel._lastBootPct   = null
        ConsoleNode.dispatch(panel, 'console:reset', {})
        super.reset(panel, graph)
    }
}

NodeRegistry.register(ConsoleNode)
