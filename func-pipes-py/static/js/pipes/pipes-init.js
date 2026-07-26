/*
  pipes-init.js
  Bootstraps the pipes rendering and graph.
  Must load AFTER pipes-runtime.js / graph-runtime.js but BEFORE index.js.

  pipes-runtime.js bundles:
    CanvasLayer, CanvasLayerGroup, all pen renderers, GraphWalker,
    LocalStorageGraphWalker, GraphHighlighter, GraphExecutor, PipesTool,
    createPipesRuntime, dispatchRequestDrawEvent, dispatchFocusNodeEvent

  graph-runtime.js bundles:
    Graph (multi-format connection store), Stepper, PipIndexStepper

  Programmatic connection API (on pipesGraph):
    pipesGraph.connect('1', '2', line?)
    pipesGraph.connectMany([ ['1','2'] ])            — listList
    pipesGraph.connectMany([ {sender:'1',receiver:'2'} ])  — listDict
    pipesGraph.connectMany({ '1': ['2','3'] })       — dictDict
*/

/*
   pipes-runtime.js (CanvasLayerGroup) calls app.getTip(label, direction, pipIndex)
   to resolve a DOM node from a pip descriptor.
*/
window.app = {
    getTip(label, direction, index = 0) {
        const nodeId = `${label}-${direction}-${index}`
        return { node: document.getElementById(nodeId) }
    }
}

// pipesWalker — GraphWalker reads from pipeData.connections, which CanvasLayerGroup
// populates automatically on every 'connectnodes' event. No shim needed.
let pipesWalker

// pipesGraph — Graph instance (graph-runtime.js) used only for the
// programmatic connect / connectMany helpers. Traversal goes through pipesWalker.
let pipesGraph

document.addEventListener('DOMContentLoaded', () => {
    // createPipesRuntime sets up CanvasLayer × 2, CanvasLayerGroup, PipesTool
    // and attaches clItems + pipesTool to window automatically.
    createPipesRuntime()
    clItems.animDraw()

    // GraphWalker uses pipeData.connections (module-internal to pipes-runtime.js).
    // It is populated by CanvasLayerGroup.connectNodes on every 'connectnodes' event,
    // so both UI drag-drop edges and programmatic edges are visible here.
    pipesWalker = new GraphWalker()

    // ── programmatic helpers (only when graph-runtime.js is loaded) ─────
    if (typeof Graph !== 'undefined') {
        pipesGraph = new Graph({ connectionsPipDicts: [] })
        pipesGraph.dataType = 'pipDict'

        pipesGraph.connect = function(a, b, line = {}) {
            const entry = this.createConnectionEntry(String(a), String(b))
            entry.line = line
            document.dispatchEvent(new CustomEvent('connectnodes', { detail: entry }))
            dispatchRequestDrawEvent()
        }

        pipesGraph.connectMany = function(pairs, line = {}) {
            if (!Array.isArray(pairs) && typeof pairs === 'object') {
                for (const [from, tos] of Object.entries(pairs)) {
                    for (const to of [].concat(tos)) this.connect(from, to, line)
                }
                return
            }
            for (const pair of pairs) {
                if (Array.isArray(pair)) {
                    this.connect(pair[0], pair[1], line)
                } else {
                    this.connect(pair.sender, pair.receiver, line)
                }
            }
        }
    }

    document.addEventListener('dragmove',  () => dispatchRequestDrawEvent())
    document.addEventListener('panspace',  () => dispatchRequestDrawEvent())
    document.addEventListener('zoomspace', () => dispatchRequestDrawEvent())
})
