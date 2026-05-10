/*
  power2/index.js — Vue App Bootstrap
  ─────────────────────────────────────────────────────────────────────────────
  Thin entry point. Creates the Graph engine then wires it to a Vue app whose
  methods are one-line delegations to node classes or the graph engine.

  Load order in power2.html:
    vendor/vue.global.prod.js
    vendor/dragsolo.js
    vendor/pipes-runtime.js
    js/pipes/pipes-init.js

    js/power2/core/node-base.js       ← NodeBase class
    js/power2/core/node-registry.js   ← NodeRegistry singleton
    js/power2/core/edge-store.js      ← EdgeStore2 singleton
    js/power2/core/graph.js           ← Graph class

    js/power2/nodes/gen.js            ← registers Generator
    js/power2/nodes/breaker.js        ← registers Breaker
    js/power2/nodes/bulb.js           ← registers Bulb
    js/power2/nodes/load.js           ← registers Load
    js/power2/nodes/meter.js          ← registers Meter
    js/power2/nodes/converter.js      ← registers Converter
    js/power2/nodes/heater.js         ← registers Heater  (custom)
    js/power2/nodes/console-node.js   ← registers ConsoleNode (custom)

    js/power2/index.js                ← this file (must be last)

  Adding a new node
  ─────────────────
  1. Create a file in js/power2/nodes/ extending NodeBase (or Load/etc.).
  2. Call NodeRegistry.register(YourClass) at the bottom.
  3. Add a <script> tag for it before index.js in power2.html.
  4. Add a toolbar button (addType('yourtype')) and a template block.
  Done — no changes to the engine required.
*/

const { createApp, nextTick } = Vue

// dragHost is declared globally by pipes-init.js / dragsolo usage
let dragHost = new DragSolo()

createApp({

    // ── Reactive state ────────────────────────────────────────────────────────

    data() {
        return {
            graphRunning:    true,
            panels:          [],
            // Toolbar / inspector state
            disconnectMode:  false,
            disconnectFirst: null,
            edgeMode:        false,
            edgeFirst:       null,
            activeEdge:      null,
            // Expose wire type catalog for the edge editor dropdown
            EdgeWireTypes:   EdgeStore2.WIRE_TYPES,
        }
    },

    computed: {
        /** Catalog entries grouped by group string — drives the toolbar <select>. */
        catalogGroups() {
            return NodeRegistry.catalogByGroup()
        },
    },

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    created() {
        // Build the graph engine, passing Vue helpers and drag utilities.
        this.graph = new PowerGraph(this, { nextTick, stickAll, dragHost })
    },

    mounted() {
        this.graph.startTick()
        window.infiniteDrag = new ZoomableInfiniteDrag('.layer-space', '.panel')
    },

    beforeUnmount() {
        this.graph.stopTick()
    },

    // ── Methods ───────────────────────────────────────────────────────────────

    methods: {

        // ── Toolbar: quick-add ───────────────────────────────────────────────
        addGen()       { this.graph.addType('gen') },
        addBreaker()   { this.graph.addType('breaker') },
        addBulb()      { this.graph.addType('bulb') },
        addLoad()      { this.graph.addType('load') },
        addMeter()     { this.graph.addType('meter') },
        addConverter() { this.graph.addType('converter') },
        addHeater()        { this.graph.addType('heater') },
        addConsole()       { this.graph.addType('console') },
        addSeriesBattery() { this.graph.addType('series-bat') },

        /** Generic add by type — used by extensions loaded at runtime. */
        addType(type, preset = {}) { this.graph.addType(type, preset) },

        /** Catalog select handler. */
        addFromCatalog(key) { this.graph.addFromCatalog(key) },

        // ── Panel lifecycle ──────────────────────────────────────────────────
        removePanel(i)      { this.graph.removePanel(i) },
        resetPanel(panel)   { this.graph.resetPanel(panel) },
        toggleEnabled(panel) { this.graph.toggleEnabled(panel) },

        // ── Generator ────────────────────────────────────────────────────────
        toggleGen(panel)        { Generator.toggle(panel, this.graph) },
        genParamsChanged(panel) { Generator.paramsChanged(panel, this.graph) },

        // ── Breaker ──────────────────────────────────────────────────────────
        toggleBreaker(panel)    { Breaker.toggle(panel, this.graph) },

        // ── Load ─────────────────────────────────────────────────────────────
        loadParamsChanged(panel) { Load.paramsChanged(panel, this.graph) },
        chargePercent(panel)     { return Load.chargePercent(panel) },

        // ── Converter ────────────────────────────────────────────────────────
        converterDialUp(panel)    { Converter.dialUp(panel, this.graph) },
        converterDialDown(panel)  { Converter.dialDown(panel, this.graph) },
        converterParamsChanged(p) { Converter.paramsChanged(p, this.graph) },

        // ── Series Battery ───────────────────────────────────────────────────
        toggleSeriesBattery(panel)        { SeriesBattery.toggle(panel, this.graph) },
        toggleSeriesBatteryPass(panel)    { SeriesBattery.togglePass(panel, this.graph) },
        seriesBatteryParamsChanged(panel) { SeriesBattery.paramsChanged(panel, this.graph) },

        // ── Decision ─────────────────────────────────────────────────────────
        addDecision()                { this.graph.addType('decision') },
        decisionReRoute(panel)       { DecisionNode.reRoute(panel, this.graph) },
        decisionSetDefault(panel, i)  { DecisionNode.setDefault(panel, i, this.graph) },

        // ── Bus Bar ───────────────────────────────────────────────────────────
        addBusBar()                          { this.graph.addType('bus-bar') },
        busBarSetWeight(panel, index, value)  { BusBar.setChannelWeight(panel, index, value, this.graph) },
        busBarEqualise(panel)                 { BusBar.equalise(panel, this.graph) },
        busBarApplyWeights(panel)             { BusBar.applyWeights(panel, this.graph) },

        // ── Ripple ───────────────────────────────────────────────────────────
        toggleRipple(panel)      { this.graph.toggleRipple(panel) },
        rippleParamsChanged(p)   { this.graph.rippleParamsChanged(p) },

        // ── Simulation toggle ────────────────────────────────────────────────
        toggleGraph() { this.graphRunning = !this.graphRunning },

        // ── Pip wiring ───────────────────────────────────────────────────────
        pipStartDrag(e, dir, pip) { this.graph.pipStartDrag(e, dir, pip) },
        pipEndDrag(e)              { this.graph.pipEndDrag(e) },
        pipOverDrag(e)             { e.preventDefault() },
        pipDrop(e, dir, pip)       { this.graph.pipDrop(e, dir, pip) },
        connect(sender, receiver)  { this.graph.connect(sender, receiver) },

        updateEdge(key, props)     { this.graph.updateEdge(key, props) },

        disconnectPip(pip)         { this.graph.disconnectPip(pip) },
        selectEdgePip(pip)         { this.graph.selectEdgePip(pip) },

        // ── Save / load / export / import ────────────────────────────────────
        saveLayout()       { this.graph.saveLayout() },
        loadLayout(json)   { this.graph.loadLayout(json) },
        exportJSON()       { this.graph.exportJSON() },
        importJSON()       { this.graph.importJSON() },
    },

}).mount('#app')
