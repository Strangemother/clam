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
        { key: 'decision-2',   label: 'Decision (2 in → 2 out)', inputCount: 2, outputCount: 2 },
        { key: 'decision-2-3', label: 'Decision (2 in → 3 out)', inputCount: 2, outputCount: 3 },
        { key: 'decision-4',   label: 'Decision (4 in → 4 out)', inputCount: 4, outputCount: 4 },
    ]

    // ── State factory ─────────────────────────────────────────────────────────

    static defaults(id, preset = {}) {
        const inCount  = preset.inputCount  ?? this.outputCount   // default same as outputs
        const outCount = preset.outputCount ?? this.outputCount
        const base     = super.defaults(id, preset)
        return {
            ...base,
            // Configuration
            inputCount:     inCount,
            outputCount:    outCount,
            tickInterval:   preset.tickInterval ?? 1.0,
            // Runtime state
            lastDecision:   null,
            defaultOutput:  0,
            decideCallback: null,
            _tickAccum:     0,
            _lastInPip:     0,
            _pipSignals:    {},           // pipIndex → last signal received on that pip
            _isDecision:    true,
            // Override pips with correct counts
            pipsInbound:  Array.from({ length: inCount  }, (_, i) => ({ label: id, index: i })),
            pipsOutbound: Array.from({ length: outCount }, (_, i) => ({ label: id, index: i })),
        }
    }

    static configFields() {
        return [...super.configFields(), 'inputCount', 'outputCount', 'tickInterval', 'defaultOutput']
    }

    // ── Core hooks ────────────────────────────────────────────────────────────

    /**
     * Called whenever an upstream signal changes on any inbound pip.
     * `panel._lastInPip` is set by graph.receive() before this is called.
     */
    static apply(panel, signal, graph) {
        const inPip = panel._lastInPip ?? 0
        // Track per-pip signal so decide() can inspect all inputs
        panel._pipSignals[inPip] = signal
        this._route(panel, signal, graph, inPip)
    }

    /**
     * Periodic re-evaluation at `tickInterval` seconds.
     * Useful for time-based routing decisions that change independently of
     * signal value — e.g. "switch to output 1 after 10 seconds of inactivity".
     */
    static tick(panel, dt, graph) {
        if (panel.enabled === false) return
        panel._tickAccum += dt
        if (panel._tickAccum >= panel.tickInterval) {
            panel._tickAccum = 0
            // Re-route using the most recently active inbound pip
            this._route(panel, panel.signal, graph, panel._lastInPip ?? 0)
        }
    }

    static reset(panel, graph) {
        panel.lastDecision = null
        panel._tickAccum   = 0
        panel._pipSignals  = {}
        panel._lastInPip   = 0
        DecisionNode.dispatch(panel, 'decision:reset', {})
        super.reset(panel, graph)
        panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
    }

    // ── Routing ───────────────────────────────────────────────────────────────

    /**
     * Evaluate decide(), then send the signal to the chosen output(s) and null
     * to all others.
     * @private
     */
    static _route(panel, signal, graph, inputIndex = 0) {
        let chosen
        try {
            chosen = this.decide(panel, signal, inputIndex, graph)
        } catch (err) {
            console.error(`[DecisionNode:${panel.id}] decide() threw:`, err)
            panel.state = 'error'
            DecisionNode.dispatch(panel, 'decision:error', { error: err.message })
            panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
            return
        }

        const prev = panel.lastDecision
        panel.lastDecision = chosen

        if (chosen === null) {
            // Block all outputs
            panel.state = signal ? 'blocked' : 'off'
            panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
            if (prev !== chosen)
                DecisionNode.dispatch(panel, 'decision:blocked', { prev, signal: !!signal })
            return
        }

        // Normalise to array to support multicast (return [0, 2] to emit to both)
        const targets = Array.isArray(chosen) ? chosen : [chosen]

        panel.pipsOutbound.forEach((_, i) => {
            graph.emitTo(panel, i, targets.includes(i) ? signal : null)
        })

        panel.state = signal ? 'routing' : 'off'

        const prevKey = JSON.stringify(prev)
        const nextKey = JSON.stringify(chosen)
        if (prevKey !== nextKey)
            DecisionNode.dispatch(panel, 'decision:routed', { from: prev, to: chosen, input: inputIndex })

        graph.updateAllGenDraws()
    }

    // ── Override this in subclasses ───────────────────────────────────────────

    /**
     * Return the output index (or array of indices) to route the signal to.
     * Return `null` to block all outputs.
     *
     * @param  {Object}      panel       — reactive panel state
     * @param  {Object|null} signal      — { v, a } or null — signal on the triggering pip
     * @param  {number}      inputIndex  — which inbound pip triggered this call
     * @param  {PowerGraph}  graph       — graph engine (rarely needed)
     * @returns {number | number[] | null}
     *
     * Access all inbound pip signals via panel._pipSignals:
     *   panel._pipSignals[0]  — last signal seen on inbound pip 0
     *   panel._pipSignals[1]  — last signal seen on inbound pip 1
     */
    static decide(panel, signal, inputIndex, graph) {
        if (typeof panel.decideCallback === 'function') {
            return panel.decideCallback(signal, inputIndex, panel, graph) ?? 0
        }
        return panel.defaultOutput ?? 0
    }

    /**
     * Null every outbound pip when the node is disabled, not just pip 0.
     */
    static onDisabled(panel, graph) {
        panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
    }

    // ── Actions ───────────────────────────────────────────────────────────────

    /** Force a manual re-route from the UI. */
    static reRoute(panel, graph) {
        panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
        this._route(panel, panel.signal, graph, panel._lastInPip ?? 0)
    }

    /** Pin a default output index from the UI. */
    static setDefault(panel, index, graph) {
        panel.defaultOutput = index
        this._route(panel, panel.signal, graph, panel._lastInPip ?? 0)
    }
}

NodeRegistry.register(DecisionNode)

class MyCustomDecision extends DecisionNode {

    static type        = 'my-decision'
    static label       = 'My Decision'
    static outputCount = 3

    static catalog = [
        { key: 'my-decision', label: 'My Decision (3 out)', outputCount: 3, inputCount: 2 },
    ]

    /**
     * Randomly routes to one of the available outputs each time a signal arrives
     * or the tick interval fires. panel._pipSignals[n] holds per-input history.
     */
    static decide(panel, signal, inputIndex, graph) {
        if (!signal) return null
        // Return a random output for demo purposes
        return Math.floor(Math.random() * panel.outputCount)
    }
}

NodeRegistry.register(MyCustomDecision)