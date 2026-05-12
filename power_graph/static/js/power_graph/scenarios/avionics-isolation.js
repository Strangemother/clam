/*
  scenarios/avionics-isolation.js  (power_graph edition)
  ─────────────────────────────────────────────────────────────────────────────
  Fix scenario: "Avionics Isolation" — Tier-2 upgrade for flying_car_v1.

  Problem:  The 48V Avionics Converter (node 19) feeds off the shared HV Bus
            (node 3). Motor inrush drags the bus voltage, the converter outputs
            proportionally less, and the Flight Computer reboots below minVolts.

  Fix (4 steps over WS ops):
    1. Spawn a clean 240V / 5A dedicated generator ("Avionics Power Cell").
    2. Wait for the server to acknowledge it and return the new node's ID.
    3. Disconnect the existing HV Bus → Avionics Converter wire (3:0->19:0).
    4. Connect the new generator → Avionics Converter, then repropagate.

  Usage (from Vue app method):
    runAvionicsIsolationFix(this, this.addLog.bind(this))

  The app instance is passed in so `sendCmd` and the reactive `panels` dict
  are available without any global references.
*/

/**
 * Wait until a panel whose ID does not appear in `knownIds` appears in
 * `app.panels`, or until `timeoutMs` elapses.
 *
 * @param   {object}   app       - Vue app instance
 * @param   {Set}      knownIds  - panel IDs that existed before the spawn
 * @param   {number}   timeoutMs
 * @returns {Promise<number|null>}  the new panel's id, or null on timeout
 */
function _waitForNewPanel(app, knownIds, timeoutMs = 3000) {
    return new Promise(resolve => {
        const deadline = Date.now() + timeoutMs
        const interval = setInterval(() => {
            for (const id of Object.keys(app.panels)) {
                if (!knownIds.has(Number(id))) {
                    clearInterval(interval)
                    resolve(Number(id))
                    return
                }
            }
            if (Date.now() > deadline) {
                clearInterval(interval)
                resolve(null)
            }
        }, 80)
    })
}

/**
 * Run the avionics isolation fix against the live power_graph WebSocket backend.
 *
 * @param {object}   app  - Vue app instance (has sendCmd, panels, addLog)
 * @param {Function} [log] - optional status callback(type, message)
 */
async function runAvionicsIsolationFix(app, log = (t, m) => console.log(`[${t}]`, m)) {
    const delay = ms => new Promise(resolve => setTimeout(resolve, ms))

    const HV_BUS_ID   = 3
    const AVI_CONV_ID = 19
    const CONN_KEY    = `${HV_BUS_ID}:0->${AVI_CONV_ID}:0`

    log('info', '🔧 Avionics Isolation Fix — starting…')
    await delay(200)

    // ── Step 1: Record existing panel IDs, then spawn the new generator ──
    log('info', 'Step 1/4 — Spawning Avionics Power Cell…')
    const knownIds = new Set(Object.keys(app.panels).map(Number))

    app.sendCmd({
        op:        'spawn',
        node_type: 'gen',
        label:     'Avionics Power Cell',
        preset: {
            volts:  240,
            amps:   5,
            live:   true,
            ripple: { enabled: false, amount: 0,  interval: 1 },
            spike:  { enabled: false, percent: 0, duration: 0 },
        },
    })

    // ── Step 2: Wait for the server to push the new panel ───────────────
    log('info', 'Step 2/4 — Waiting for server acknowledgement…')
    const newGenId = await _waitForNewPanel(app, knownIds)

    if (newGenId === null) {
        log('err', 'Avionics Isolation: timeout waiting for spawned node — aborting.')
        return
    }
    log('info', `Step 2/4 — New generator registered as node ${newGenId}`)
    await delay(300)

    // ── Step 3: Cut the HV Bus → Avionics Converter wire ────────────────
    log('info', `Step 3/4 — Disconnecting ${CONN_KEY}…`)
    app.sendCmd({ op: 'disconnect', conn_key: CONN_KEY })
    await delay(400)

    // ── Step 4: Connect new generator → Avionics Converter ──────────────
    log('info', `Step 4/4 — Connecting node ${newGenId} → Avionics Converter…`)
    app.sendCmd({
        op:       'connect',
        from_id:  newGenId,
        from_pip: 0,
        to_id:    AVI_CONV_ID,
        to_pip:   0,
        wire:     { wireType: 'copper', length: 150 },
    })
    await delay(300)

    app.sendCmd({ op: 'repropagate' })
    log('info', '✅ Avionics Isolation complete — avionics rail is now independent of the motor bus.')
}
