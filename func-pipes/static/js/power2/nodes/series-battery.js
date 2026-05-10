/*
  nodes/series-battery.js — Rechargeable Battery / Supercapacitor
  ─────────────────────────────────────────────────────────────────────────────
  A rechargeable battery with both an inbound (charging) pip and an outbound
  (output) pip. It operates independently of the inbound voltage — it always
  emits its own rated EMF (panel.volts) downstream. The inbound signal purely
  charges the energy store; the outbound load draws from it.

  Energy model
  ────────────
  Each tick:
    chargeInW   = V_in × min(A_in, chargeAmps)   — power arriving from charger
    chargeOutW  = drawWatts                        — actual downstream load (BFS)
    net (W)     = chargeInW − chargeOutW
    ΔchargeWh   = net × dt / 3600

  If chargeWh > 0 the battery emits its own { v: panel.volts, a: panel.amps }
  regardless of whether anything is connected to the inbound pip.
  When chargeWh reaches 0 the battery goes 'dead' and emits null.
  It auto-revives as soon as enough charge has accumulated (> 1% capacity).

  States: 'off' | 'charging' | 'discharging' | 'full' | 'dead'

  Extended state
  ──────────────
  live          bool    — output enabled; false = no EMF out
  volts         number  — rated output voltage (default 12)
  amps          number  — rated max output current (default 20)
  chargeAmps    number  — max inbound charge current accepted (default 10)
  capacityWh    number  — total energy capacity in watt-hours (default 10)
  chargeWh      number  — current stored energy
  chargePercent number  — 0–100 live readout
  drawWatts     number  — downstream load draw, updated by BFS each frame
  chargeInW     number  — live inbound charge power (W)
  chargeOutW    number  — live outbound draw power (W)
  inVolts       number  — live inbound voltage readout
  inAmps        number  — live inbound current readout
*/

class SeriesBattery extends NodeBase {

    static type  = 'series-bat'
    static label = 'Battery'
    static group = 'Source'

    static catalog = [
        { key: 'series-12v',   label: 'Battery 12V 10Ah',   volts: 12,  amps: 20,  chargeAmps: 10, capacityWh: 120  },
        { key: 'series-24v',   label: 'Battery 24V 10Ah',   volts: 24,  amps: 20,  chargeAmps: 10, capacityWh: 240  },
        { key: 'series-48v',   label: 'Battery 48V 20Ah',   volts: 48,  amps: 30,  chargeAmps: 15, capacityWh: 960  },
        { key: 'series-lipo',  label: 'LiPo 3.7V  5Ah',     volts: 3.7, amps: 10,  chargeAmps: 5,  capacityWh: 18.5 },
        { key: 'series-9v',    label: 'PP3  9V  0.5Ah',      volts: 9,   amps: 1,   chargeAmps: 0.5,capacityWh: 4.5  },
        { key: 'series-super', label: 'Supercap 12V 0.1Wh',  volts: 12,  amps: 50,  chargeAmps: 50, capacityWh: 0.1  },
    ]

    static _defaultRipple() {
        return { enabled: false, amount: 0.5, interval: 0.5 }
    }

    static defaults(id, preset = {}) {
        const cap = preset.capacityWh ?? 10
        return {
            ...super.defaults(id, preset),
            label:         preset.label      || 'Battery',
            volts:         preset.volts      ?? 12,
            amps:          preset.amps       ?? 20,
            chargeAmps:    preset.chargeAmps ?? 10,
            capacityWh:    cap,
            chargeWh:      cap,
            chargePercent: 100,
            drawWatts:     0,
            chargeInW:     0,
            chargeOutW:    0,
            inVolts:       0,
            inAmps:        0,
            live:          true,
            ripple:        preset.ripple ? { ...preset.ripple } : { ...this._defaultRipple() },
        }
    }

    static configFields() {
        return [...super.configFields(), 'volts', 'amps', 'chargeAmps', 'capacityWh', 'live', 'ripple']
    }

    static apply(panel, signal, graph) {
        // Store inbound signal for charge calculation in tick
        panel.inVolts = signal ? signal.v : 0
        panel.inAmps  = signal ? signal.a : 0

        if (panel.state === 'dead') {
            graph.emit(panel, null)
            return
        }

        if (!panel.live) {
            // Pass-through: forward inbound signal unchanged, no charge used
            if (signal && signal.v > 0) {
                panel.state = 'pass'
                graph.emit(panel, { v: signal.v, a: Math.min(signal.a, panel.amps) })
            } else {
                panel.state = 'off'
                graph.emit(panel, null)
            }
            return
        }

        if (panel.chargeWh <= 0) {
            panel.state    = 'dead'
            panel.chargeWh = 0
            graph.emit(panel, null)
            graph.updateAllGenDraws()
            return
        }

        // Emit own rated EMF stacked on top of inbound voltage
        const vIn  = signal ? signal.v : 0
        const aOut = signal ? Math.min(signal.a, panel.amps) : panel.amps
        const vOff = panel._rippleOffset ?? 0
        graph.emit(panel, { v: vIn + panel.volts + vOff, a: aOut })
    }

    static tick(panel, dt, graph) {
        // Charging and discharging are independent processes.
        //
        // Charge in: inbound source pushes current into the battery at up to
        //   chargeAmps, stored at the battery's own voltage.
        //   chargeInW = min(A_in, chargeAmps) × V_bat
        //
        // Charge out: the battery's proportional share of the downstream load.
        //   In a series stack, each source's share ∝ its voltage fraction.
        //   chargeOutW = drawWatts × V_bat / (V_in + V_bat)
        //   When standalone (V_in = 0) this correctly equals drawWatts.

        const totalV     = panel.inVolts + panel.volts
        const chargeInW  = (panel.inVolts > 0)
            ? Math.min(panel.inAmps, panel.chargeAmps) * panel.volts
            : 0
        const chargeOutW = (panel.live && totalV > 0 && panel.drawWatts > 0)
            ? panel.drawWatts * (panel.volts / totalV)
            : 0

        panel.chargeInW  = +chargeInW.toFixed(1)
        panel.chargeOutW = +chargeOutW.toFixed(1)

        const netW = chargeInW - chargeOutW
        panel.chargeWh = Math.min(
            panel.capacityWh,
            Math.max(0, panel.chargeWh + (netW * dt) / 3600)
        )
        panel.chargePercent = +(panel.chargeWh / panel.capacityWh * 100).toFixed(1)

        if (panel.state === 'dead') {
            if (panel.chargeWh >= panel.capacityWh * 0.01 && chargeInW > 0) {
                panel.state = 'charging'
                panel.live  = true
                SeriesBattery.apply(panel, panel.signal, graph)
                graph.updateAllGenDraws()
            }
            return
        }

        if (panel.chargeWh <= 0) {
            panel.state = 'dead'
            panel.live  = false
            graph.emit(panel, null)
            graph.updateAllGenDraws()
            return
        }

        if (!panel.live) { panel.state = panel.signal?.v > 0 ? 'pass' : 'off'; return }

        if (panel.chargeWh >= panel.capacityWh) {
            panel.state = 'full'
        } else if (netW >= 0) {
            panel.state = 'charging'
        } else {
            panel.state = 'discharging'
        }
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    static toggle(panel, graph) {
        if (panel.state === 'dead') return   // must reset first
        panel.live = !panel.live
        SeriesBattery.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    // Switch to pass-through mode (live=false keeps signal flowing unchanged)
    static togglePass(panel, graph) {
        if (panel.state === 'dead') return
        if (!panel.live) {
            // already in pass-through → switch back to boost
            panel.live = true
        } else {
            panel.live = false
        }
        SeriesBattery.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    static paramsChanged(panel, graph) {
        if (panel.chargeWh > panel.capacityWh) panel.chargeWh = panel.capacityWh
        panel.chargePercent = +(panel.chargeWh / panel.capacityWh * 100).toFixed(1)
        SeriesBattery.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    static reset(panel, graph) {
        panel.live          = true
        panel.chargeWh      = panel.capacityWh
        panel.chargePercent = 100
        panel.drawWatts     = 0
        panel.chargeInW     = 0
        panel.chargeOutW    = 0
        panel.inVolts       = 0
        panel.inAmps        = 0
        super.reset(panel, graph)
    }
}

NodeRegistry.register(SeriesBattery)
