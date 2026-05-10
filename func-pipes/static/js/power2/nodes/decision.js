/*
  nodes/decision.js — Decision / Router Node
  ─────────────────────────────────────────────────────────────────────────────
  Routes an inbound signal to one (or many) of its N outbound outputs based on
  a user-defined `decide()` function evaluated every tick and on every signal
  arrival.

  Designed for clean subclassing:

      class VoltageRouter extends DecisionNode {
          static type        = 'volt-router'
          static label       = 'Voltage Router'
          static outputCount = 3

          static defaults(id, preset = {}) {
              return { ...super.defaults(id, preset), minVolt: preset.minVolt ?? 180 }
          }

          // Return output index, array of indices (multicast), or null (block all).
          static decide(panel, signal) {
              if (!signal) return null
              if (signal.v >= 200) return 0
              if (signal.v >= panel.minVolt) return 1
              return 2
          }
      }

      NodeRegistry.register(VoltageRouter)

  Runtime callback (no subclass needed):

      const panel = graph.addType('decision')
      panel.decideCallback = (signal, panel) => signal?.v > 150 ? 0 : 1

  Extended state
  ──────────────
  outputCount     number    — how many outbound pips (set at creation via preset)
  tickInterval    number    — seconds between tick-driven re-evaluations (default 1.0)
  lastDecision    number|null — output index(es) chosen on last decide() call
  decideCallback  function|null — optional runtime override for decide()

  States: 'off' | 'routing' | 'blocked' | 'error'
*/

class DecisionNode extends NodeBase {

    static type        = 'decision'
    static label       = 'Decision'
    static group       = 'Control'
    static outputCount = 2              // default: 2 outputs; override in subclass

    static catalog = [
        { key: 'decision-2', label: 'Decision (2 out)', outputCount: 2 },
        { key: 'decision-3', label: 'Decision (3 out)', outputCount: 3 },
        { key: 'decision-4', label: 'Decision (4 out)', outputCount: 4 },
    ]

    // ── State factory ─────────────────────────────────────────────────────────

    static defaults(id, preset = {}) {
        const count = preset.outputCount ?? this.outputCount
        const base  = super.defaults(id, preset)
        return {
            ...base,
            // Configuration
            outputCount:    count,
            tickInterval:   preset.tickInterval ?? 1.0,   // seconds between tick re-evals
            // Runtime state
            lastDecision:   null,          // last chosen output (index or array)
            defaultOutput:  0,             // user-pinned default; used by base decide()
            decideCallback: null,          // panel-level override function
            _tickAccum:     0,
            // Regenerate pipsOutbound with the correct count (overrides super's single pip)
            pipsOutbound: Array.from({ length: count }, (_, i) => ({ label: id, index: i })),
        }
    }

    static configFields() {
        return [...super.configFields(), 'outputCount', 'tickInterval', 'defaultOutput']
    }

    // ── Core hooks ────────────────────────────────────────────────────────────

    /**
     * Called whenever the upstream signal changes.
     * Routes immediately so power flows without waiting for the next tick.
     */
    static apply(panel, signal, graph) {
        this._route(panel, signal, graph)
    }

    /**
     * Periodic re-evaluation at `tickInterval` seconds.
     * Useful for time-based routing decisions that change independently of
     * signal value — e.g. "switch to output 1 after 10 seconds of inactivity".
     */
    static tick(panel, dt, graph) {
        panel._tickAccum += dt
        if (panel._tickAccum >= panel.tickInterval) {
            panel._tickAccum = 0
            this._route(panel, panel.signal, graph)
        }
    }

    static reset(panel, graph) {
        panel.lastDecision = null
        panel._tickAccum   = 0
        super.reset(panel, graph)
        // Null all outputs on reset
        panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
    }

    // ── Routing ───────────────────────────────────────────────────────────────

    /**
     * Evaluate decide(), then send the signal to the chosen output(s) and null
     * to all others.
     * @private
     */
    static _route(panel, signal, graph) {
        let chosen
        try {
            chosen = this.decide(panel, signal, graph)
        } catch (err) {
            console.error(`[DecisionNode:${panel.id}] decide() threw:`, err)
            panel.state = 'error'
            panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
            return
        }

        panel.lastDecision = chosen

        if (chosen === null) {
            // Block all outputs
            panel.state = signal ? 'blocked' : 'off'
            panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
            return
        }

        // Normalise to array to support multicast (return [0, 2] to emit to both)
        const targets = Array.isArray(chosen) ? chosen : [chosen]

        panel.pipsOutbound.forEach((_, i) => {
            graph.emitTo(panel, i, targets.includes(i) ? signal : null)
        })

        panel.state = signal ? 'routing' : 'off'
    }

    // ── Override this in subclasses ───────────────────────────────────────────

    /**
     * Return the output index (or array of indices) to route the signal to.
     * Return `null` to block all outputs.
     *
     * @param  {Object}      panel   — reactive panel state (read your config here)
     * @param  {Object|null} signal  — { v, a } or null
     * @param  {PowerGraph}  graph   — graph engine (rarely needed)
     * @returns {number | number[] | null}
     */
    static decide(panel, signal, graph) {
        // Runtime callback takes priority (panel.decideCallback set from outside)
        if (typeof panel.decideCallback === 'function') {
            return panel.decideCallback(signal, panel, graph) ?? 0
        }
        // Fall back to the user-pinned default (set via UI or panel.defaultOutput)
        return panel.defaultOutput ?? 0
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    /** Force a manual re-route from the UI. */
    static reRoute(panel, graph) {
        this._route(panel, panel.signal, graph)
    }

    /**
     * Pin a default output index from the UI.
     * Subclass decide() can read panel.defaultOutput and choose to honour it.
     */
    static setDefault(panel, index, graph) {
        panel.defaultOutput = index
        this._route(panel, panel.signal, graph)
    }
}

NodeRegistry.register(DecisionNode)
