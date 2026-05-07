/*
  pipes-init.js
  Bootstraps the canvas drawing layers and graph walker for chat panels.
  Must load AFTER canvas-layer.js / graph-walker.js but BEFORE index-vue.js.
*/

/* ── pipe event helpers (no PetiteVue dependency) ──────────────────────── */

const dispatchRequestDrawEvent = (data = {}) =>
    document.dispatchEvent(new CustomEvent('requestdraw', { detail: data }))

const dispatchFocusNodeEvent = (data = {}) =>
    document.dispatchEvent(new CustomEvent('focusnode', { detail: data }))

const listenEvent = (name, cb, opts = { passive: true }) =>
    document.addEventListener(name, cb, opts)

/* ── global `app` proxy required by canvas-layer.js ──────────────────── */
/*
   canvas-layer.js calls app.getTip(label, direction, pipIndex) to resolve
   a DOM node from a pip descriptor.  We satisfy that with a simple id lookup.
   The label used in pip :id attributes is the panel's numeric id.
*/
window.app = {
    getTip(label, direction, index = 0) {
        const nodeId = `${label}-${direction}-${index}`
        return { node: document.getElementById(nodeId) }
    }
}

/* ── canvas layers + walker, initialised after DOM is ready ─────────── */

let clItems       // CanvasLayerGroup
let pipesWalker   // GraphWalker

document.addEventListener('DOMContentLoaded', () => {
    const cl1 = new CanvasLayer('.canvas-container.back canvas')
    const cl2 = new CanvasLayer('.canvas-container.fore canvas')
    clItems = new CanvasLayerGroup(cl1, cl2)
    pipesWalker = new GraphWalker()  // uses pipeData.connections from canvas-layer.js
    clItems.animDraw()

    // Redraw whenever a panel is dragged
    document.addEventListener('dragmove',  () => dispatchRequestDrawEvent())
    document.addEventListener('panspace',  () => dispatchRequestDrawEvent())
    document.addEventListener('zoomspace', () => dispatchRequestDrawEvent())
})
