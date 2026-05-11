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

    static _defaultSpike() {
        return { enabled: true, percent: 10, duration: 0.3 }
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
            spike:         preset.spike  ? { ...preset.spike  } : { ...this._defaultSpike()  },
        }
    }

    static configFields() {
        return [...super.configFields(), 'volts', 'amps', 'chargeAmps', 'capacityWh', 'live', 'ripple', 'spike']
    }

    /**
     * Process an inbound (charging) signal. When live, adds the battery's own
     * rated EMF on top of the inbound voltage and forwards downstream. When
     * not live, forwards the inbound signal unchanged (pass-through mode).
     * Emits null if the battery is dead or has no charge.
     * @param {Object}     panel
     * @param {Object|null} signal — upstream { v, a } or null
     * @param {PowerGraph} graph
     */
    static apply(panel, signal, graph) {
        // Store inbound signal for charge calculation in tick
        panel.inVolts = signal ? signal.v : 0
        panel.inAmps  = signal ? signal.a : 0

        if (panel.state === 'dead') {
            graph.emit(panel, null)
            return
        }

        const prev = panel.state

        if (!panel.live) {
            // Pass-through: forward inbound signal unchanged, no charge used
            if (signal && signal.v > 0) {
                panel.state = 'pass'
                graph.emit(panel, { v: signal.v, a: Math.min(signal.a, panel.amps) })
            } else {
                panel.state = 'off'
                graph.emit(panel, null)
            }
            if (panel.state !== prev)
                SeriesBattery.dispatch(panel, 'state:change', { from: prev, to: panel.state })
            return
        }

        if (panel.chargeWh <= 0) {
            panel.state    = 'dead'
            panel.chargeWh = 0
            SeriesBattery.dispatch(panel, 'battery:dead', { chargePercent: 0 })
            SeriesBattery.dispatch(panel, 'state:change', { from: prev, to: 'dead' })
            graph.emit(panel, null)
            graph.updateAllGenDraws()
            return
        }

        // Emit own rated EMF stacked on top of inbound voltage
        const vIn  = signal ? signal.v : 0
        const aOut = signal ? Math.min(signal.a, panel.amps) : panel.amps
        const vOff = panel._rippleOffset ?? 0
        const m    = NodeBase.spikeMultiplier(panel)
        graph.emit(panel, { v: (vIn + panel.volts + vOff) * m, a: aOut * m })
    }

    /**
     * Per-frame energy accounting. Decays any inrush spike, then independently
     * computes charge-in (from inbound source) and charge-out (proportional
     * share of downstream load) and updates chargeWh. Transitions between
     * charging / discharging / full / dead states and revives the battery once
     * enough charge has accumulated after a dead event.
     * @param {Object}     panel
     * @param {number}     dt    — elapsed seconds since last tick
     * @param {PowerGraph} graph
     */
    static tick(panel, dt, graph) {
        // Decay inrush spike and re-apply to settle downstream on expiry too.
        const wasNonZero = (panel._spikeTimer ?? 0) > 0
        const active     = NodeBase.tickSpike(panel, dt)
        if ((active || (wasNonZero && !active)) &&
                panel.live && panel.state !== 'dead' && panel.signal !== undefined)
            SeriesBattery.apply(panel, panel.signal, graph)

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

        const prevState = panel.state

        if (panel.state === 'dead') {
            if (panel.chargeWh >= panel.capacityWh * 0.01 && chargeInW > 0) {
                panel.state = 'charging'
                panel.live  = true
                SeriesBattery.dispatch(panel, 'battery:revived', { chargePercent: panel.chargePercent })
                SeriesBattery.dispatch(panel, 'state:change', { from: 'dead', to: 'charging' })
                SeriesBattery.apply(panel, panel.signal, graph)
                graph.updateAllGenDraws()
            }
            return
        }

        if (panel.chargeWh <= 0) {
            panel.state = 'dead'
            panel.live  = false
            SeriesBattery.dispatch(panel, 'battery:dead', { chargePercent: 0 })
            SeriesBattery.dispatch(panel, 'state:change', { from: prevState, to: 'dead' })
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

        if (panel.state !== prevState)
            SeriesBattery.dispatch(panel, 'state:change', { from: prevState, to: panel.state })

        // Charge telemetry — throttled, dispatched only when value changes
        const pct = panel.chargePercent
        if (pct !== panel._lastChargePct) {
            panel._lastChargePct = pct
            SeriesBattery.throttle(panel, 'battery:charge', {
                chargePercent: pct,
                chargeWh:      +panel.chargeWh.toFixed(3),
                chargeInW:     panel.chargeInW,
                chargeOutW:    panel.chargeOutW,
            })
        }
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    /**
     * Toggle battery output on or off. No-op if the battery is dead —
     * call reset() first to restore it. Starts an inrush spike when enabling.
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static toggle(panel, graph) {
        if (panel.state === 'dead') return   // must reset first
        panel.live = !panel.live
        if (panel.live) NodeBase.startSpike(panel)
        SeriesBattery.dispatch(panel, 'battery:toggle', { live: panel.live })
        SeriesBattery.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    /**
     * Toggle between boost mode (live=true, adds own EMF) and pass-through
     * mode (live=false, forwards inbound signal with no voltage addition).
     * No-op if the battery is dead.
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static togglePass(panel, graph) {
        if (panel.state === 'dead') return
        if (!panel.live) {
            // already in pass-through → switch back to boost
            panel.live = true
        } else {
            panel.live = false
        }
        SeriesBattery.dispatch(panel, 'battery:pass-toggle', { live: panel.live })
        SeriesBattery.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    /**
     * Validate and re-apply after external config changes (e.g. capacityWh or
     * chargeAmps edited via the config panel). Clamps chargeWh to capacity.
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static paramsChanged(panel, graph) {
        if (panel.chargeWh > panel.capacityWh) panel.chargeWh = panel.capacityWh
        panel.chargePercent = +(panel.chargeWh / panel.capacityWh * 100).toFixed(1)
        SeriesBattery.apply(panel, panel.signal, graph)
        graph.updateAllGenDraws()
    }

    /**
     * Full reset — restores the battery to 100% charge, re-enables output,
     * clears all telemetry accumulators, and delegates to NodeBase.reset().
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static reset(panel, graph) {
        panel.live          = true
        panel.chargeWh      = panel.capacityWh
        panel.chargePercent = 100
        panel.drawWatts     = 0
        panel.chargeInW     = 0
        panel.chargeOutW    = 0
        panel.inVolts       = 0
        panel.inAmps        = 0
        panel._lastChargePct = null
        SeriesBattery.dispatch(panel, 'battery:reset', { chargePercent: 100 })
        super.reset(panel, graph)
    }
}

NodeRegistry.register(SeriesBattery)
