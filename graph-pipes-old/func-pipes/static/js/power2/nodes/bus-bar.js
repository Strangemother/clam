/*
  nodes/bus-bar.js — Bus Bar / Power Distribution Node
  ─────────────────────────────────────────────────────────────────────────────
  Accepts one inbound signal and distributes it across N outbound outputs.
  Each output receives a fraction of the input power, proportional to a
  user-configurable weight (percentage) per channel.

  By default all channels share the input equally (balanced splitter).  The
  user can "dial in" individual channel weights — the engine always normalises
  the weights to 100 % so the distribution is self-consistent regardless of
  the raw numbers entered.

  Example — 4 outputs, default equal split:
      weights = [25, 25, 25, 25]  →  each output gets 25 % of input

  Example — 4 outputs, custom dial:
      weights = [50, 30, 10, 10]  →  outputs get 50 %, 30 %, 10 %, 10 %
      (BusBar normalises: total = 100, so fractions stay as given)

  Example — uneven raw numbers:
      weights = [2, 1, 1]  →  normalised to [50 %, 25 %, 25 %]

  A null (no-power) input silences all outputs.

  Extended state (beyond DecisionNode)
  ──────────────────────────────────────
  weights         number[]  — raw per-channel weights (user editable)
  outputCount     number    — number of output channels
  _normWeights    number[]  — normalised 0-1 fractions (internal, recomputed)

  States: 'off' | 'routing' | 'error'

  Subclassing example
  ────────────────────
      class PowerRail extends BusBar {
          static type        = 'power-rail'
          static label       = 'Power Rail'
          static outputCount = 6
          static catalog = [
              { key: 'power-rail-6', label: 'Power Rail (6 ch)', outputCount: 6 },
          ]
      }
      NodeRegistry.register(PowerRail)
*/

class BusBar extends DecisionNode {

    static type        = 'bus-bar'
    static label       = 'Bus Bar'
    static group       = 'Distribution'
    static outputCount = 4          // default channel count; override in subclass

    static catalog = [
        { key: 'bus-bar-2',  label: 'Bus Bar (2 ch)',  outputCount: 2, inputCount: 1 },
        { key: 'bus-bar-4',  label: 'Bus Bar (4 ch)',  outputCount: 4, inputCount: 1 },
        { key: 'bus-bar-6',  label: 'Bus Bar (6 ch)',  outputCount: 6, inputCount: 1 },
        { key: 'bus-bar-8',  label: 'Bus Bar (8 ch)',  outputCount: 8, inputCount: 1 },
    ]

    // ── State factory ──────────────────────────────────────────────────────

    static defaults(id, preset = {}) {
        const outCount = preset.outputCount ?? this.outputCount
        const base     = super.defaults(id, preset)

        // Start with equal weights (e.g. 4 channels → [25, 25, 25, 25])
        const defaultWeight = parseFloat((100 / outCount).toFixed(4))
        const weights = preset.weights
            ? [...preset.weights]
            : Array(outCount).fill(defaultWeight)

        return {
            ...base,
            // Bus Bar always has exactly one inbound pip
            inputCount:     1,
            outputCount:    outCount,
            pipsInbound:    [{ label: id, index: 0 }],
            pipsOutbound:   Array.from({ length: outCount }, (_, i) => ({ label: id, index: i })),
            weights,
            _normWeights:   BusBar._normalise(weights),
            // DecisionNode fields we do not use for routing logic
            tickInterval:   1.0,
            lastDecision:   null,
            defaultOutput:  0,
            decideCallback: null,
            // Template discriminators
            _isBusBar:      true,
            _isDecision:    false,
        }
    }

    static configFields() {
        return [...super.configFields(), 'outputCount', 'weights', 'ripple']
    }

    // ── Signal processing ─────────────────────────────────────────────────

    /**
     * Distribute the incoming signal proportionally across all output channels.
     * Null input → all channels silenced.
     */
    static apply(panel, signal, graph) {
        const prev = panel.state

        if (!signal) {
            panel.state = 'off'
            if (prev !== 'off') BusBar.dispatch(panel, 'state:change', { from: prev, to: 'off' })
            panel.pipsOutbound.forEach((_, i) => graph.emitTo(panel, i, null))
            return
        }

        // Recompute in case weights were mutated directly (e.g. by UI binding)
        panel._normWeights = BusBar._normalise(panel.weights)

        panel.state = 'routing'
        if (prev !== 'routing') BusBar.dispatch(panel, 'state:change', { from: prev, to: 'routing' })

        panel.pipsOutbound.forEach((_, i) => {
            const frac = panel._normWeights[i] ?? 0
            if (frac <= 0) {
                graph.emitTo(panel, i, null)
            } else {
                graph.emitTo(panel, i, {
                    v: signal.v,
                    a: signal.a * frac,
                })
            }
        })

        graph.updateAllGenDraws()
    }

    // ── Override tick: rebroadcast on every tick so live changes propagate ──

    /**
     * No-op tick. BusBar distributes purely in response to signal changes
     * via apply(); there is no time-driven rerouting logic required.
     * @param {Object}     panel
     * @param {number}     dt
     * @param {PowerGraph} graph
     */
    static tick(panel, dt, graph) {
        // No tick-driven rerouting needed — signal changes drive apply() directly.
    }

    // ── Actions ────────────────────────────────────────────────────────────

    /**
     * Set the weight for a single channel (0-100 range, arbitrary units).
     * All other channel weights remain unchanged; the engine renormalises.
     *
     * @param {Object}     panel  — reactive panel state
     * @param {number}     index  — output channel index
     * @param {number}     value  — new raw weight for this channel
     * @param {PowerGraph} graph
     */
    static setChannelWeight(panel, index, value, graph) {
        if (index < 0 || index >= panel.weights.length) return
        panel.weights[index]  = Math.max(0, value)
        panel._normWeights    = BusBar._normalise(panel.weights)
        this.apply(panel, panel.signal, graph)
        BusBar.dispatch(panel, 'busbar:weight-changed', {
            index,
            weight: panel.weights[index],
            normWeights: panel._normWeights,
        })
    }

    /**
     * Renormalise and re-emit after weights have already been updated in-place
     * (e.g. by a v-model binding in the template).
     *
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static applyWeights(panel, graph) {
        panel._normWeights = BusBar._normalise(panel.weights)
        this.apply(panel, panel.signal, graph)
    }

    /**
     * Reset all channel weights to equal distribution.
     *
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static equalise(panel, graph) {
        const count         = panel.weights.length
        const equal         = parseFloat((100 / count).toFixed(4))
        panel.weights       = Array(count).fill(equal)
        panel._normWeights  = BusBar._normalise(panel.weights)
        this.apply(panel, panel.signal, graph)
        BusBar.dispatch(panel, 'busbar:equalised', { weights: panel.weights })
    }

    /**
     * Re-normalise channel weights and propagate to NodeBase.reset().
     * Weights themselves are preserved across resets so the user's dial
     * configuration survives a graph restart.
     * @param {Object}     panel
     * @param {PowerGraph} graph
     */
    static reset(panel, graph) {
        panel._normWeights = BusBar._normalise(panel.weights)
        BusBar.dispatch(panel, 'busbar:reset', { outputCount: panel.outputCount })
        super.reset(panel, graph)
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    /**
     * Normalise an array of raw weight values into 0-1 fractions that sum to 1.
     * All-zero input yields equal fractions as a fallback.
     *
     * @param  {number[]} weights
     * @returns {number[]}
     */
    static _normalise(weights) {
        const total = weights.reduce((s, w) => s + Math.max(0, w), 0)
        if (total === 0) {
            // Fallback: equal split
            const eq = 1 / weights.length
            return weights.map(() => eq)
        }
        return weights.map(w => Math.max(0, w) / total)
    }

    /**
     * Return the effective percentage (0-100) for each channel, rounded to 2 dp.
     * Convenience method for UI display.
     *
     * @param  {Object} panel
     * @returns {number[]}
     */
    static channelPercents(panel) {
        const norm = BusBar._normalise(panel.weights)
        return norm.map(f => Math.round(f * 10000) / 100)
    }
}

NodeRegistry.register(BusBar)
