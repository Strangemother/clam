/*
  scenarios/avionics-isolation.js
  ─────────────────────────────────────────────────────────────────────────────
  "Fix Me" scenario — Tier 2 avionics brownout fix for flying_car_v1.

  Challenge:
    The 48V Avionics Converter shares the same HV Bus as the motor subsystem.
    Motor inrush drags bus voltage, the converter outputs proportionally less,
    and the Flight Computer reboots below its minVolts:40 threshold.

  What this scenario does (in order):
    1. Spawns a new "Avionics Power Cell" generator — clean 240V, no ripple.
    2. Disconnects the HV Bus (id 3) → Avionics Converter (id 19) wire.
    3. Connects the new generator directly to the Avionics Converter.
    4. Sets the new edge to a short copper run (150px).

  Assumptions:
    • The flying_car_v1 layout is loaded — HV Bus is id 3, Avionics Conv is id 19.
    • `graph` is a PowerGraph instance (from index.js: this.graph).
    • A notify(msg) helper is optional; falls back to console.log.

  Usage (from Vue app method):
    runAvionicsIsolationFix(this.graph, this.scenarioNotify.bind(this))
*/

/**
 * Disconnect the wire between two pips by directly invoking the graph's
 * two-step disconnect mechanism programmatically.
 *
 * @param {PowerGraph} graph
 * @param {number}     fromLabel   - outbound panel id
 * @param {number}     fromPipIdx  - outbound pip index (usually 0)
 * @param {number}     toLabel     - inbound panel id
 * @param {number}     toPipIdx    - inbound pip index (usually 0)
 */
function _scenarioDisconnect(graph, fromLabel, fromPipIdx, toLabel, toPipIdx) {
    // Prime the two-step disconnect with the first pip, then fire the second.
    graph.app.disconnectFirst = { pip: { label: fromLabel, index: fromPipIdx } }
    graph.disconnectPip({ label: toLabel, index: toPipIdx })
}

/**
 * Position a panel element at (left, top) after the next Vue tick.
 *
 * @param {PowerGraph} graph
 * @param {number}     panelId
 * @param {string}     left   - CSS left value e.g. "400px"
 * @param {string}     top    - CSS top value e.g. "700px"
 */
async function _scenarioPlace(graph, panelId, left, top) {
    await graph.nextTick()
    const ref = graph.app.$refs[`panel-${panelId}`]
    const el  = Array.isArray(ref) ? ref[0] : ref
    if (el) { el.style.left = left; el.style.top = top }
}

/**
 * Run the avionics isolation fix scenario.
 *
 * @param {PowerGraph}    graph   - the live PowerGraph instance
 * @param {Function}      [log]   - optional status callback(message: string)
 */
async function runAvionicsIsolationFix(graph, log = console.log) {
    const delay = ms => new Promise(resolve => setTimeout(resolve, ms))

    const HV_BUS_ID      = 3
    const AVI_CONV_ID    = 19
    const NEW_GEN_LEFT   = '200px'
    const NEW_GEN_TOP    = '700px'

    log('🔧 Starting: Avionics Isolation Fix…')
    await delay(300)

    // ── Step 1: Spawn clean dedicated avionics generator ────────────────────
    log('Step 1 / 4 — Spawning Avionics Power Cell…')

    graph.addType('gen', {
        label: 'Avionics Power Cell',
        volts: 240,
        amps: 5,
        live: true,
        ripple:  { enabled: false, amount: 0,  interval: 1 },
        spike:   { enabled: false, percent: 0, duration: 0 },
    })

    const newGen      = graph.panels[graph.panels.length - 1]
    const newGenId    = newGen.id
    newGen.title      = 'Avionics Power Cell'

    await _scenarioPlace(graph, newGenId, NEW_GEN_LEFT, NEW_GEN_TOP)
    await delay(600)

    // ── Step 2: Cut the shared HV Bus → Avionics Converter wire ─────────────
    log('Step 2 / 4 — Isolating Avionics Converter from HV Bus…')

    _scenarioDisconnect(graph, HV_BUS_ID, 0, AVI_CONV_ID, 0)

    await delay(600)

    // ── Step 3: Wire new generator → Avionics Converter ─────────────────────
    log('Step 3 / 4 — Connecting Avionics Power Cell to Converter…')

    graph.connect(
        { label: newGenId, direction: 'outbound', pipIndex: 0 },
        { label: AVI_CONV_ID, direction: 'inbound', pipIndex: 0 }
    )

    await delay(400)

    // ── Step 4: Set clean short copper run ───────────────────────────────────
    log('Step 4 / 4 — Configuring dedicated wire (copper, 150px)…')

    graph.updateEdge(`${newGenId}-0-${AVI_CONV_ID}-0`, {
        wireType: 'copper',
        length:   150,
        manualResistance: null,
    })

    await delay(300)

    log('✅ Done — Avionics are now isolated from the motor bus.')
}
