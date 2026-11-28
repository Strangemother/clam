# pipes/

Shared runtime bootstrap. Every sub-app loads this.

## What it does

`pipes-init.js` wires together the vendor canvas renderer and the graph
walker into two globals the rest of the app uses for signal routing.

## Globals it creates

| Global | Type | Purpose |
|--------|------|---------|
| `pipesWalker` | `GraphWalker` | Query connections by panel id. `getConnections(id)`, `getOutgoingIds(id)` |
| `pipesGraph` | `Graph` | Programmatic connect/disconnect. `pipesGraph.connect('1','2')` |
| `clItems` | `CanvasLayerGroup` | Canvas layer pair. `clItems.animDraw()` redraws |
| `window.app.getTip` | function | Resolves a pip DOM element by `(label, direction, index)`. Required by the renderer |

## Load order

```
pipes-runtime.js   (vendor)
graph-runtime.js   (vendor)
pipes-init.js      (this dir)
```

Always load these before any app module that calls `pipesWalker` or dispatches
`connectnodes` events.

## connectnodes event

Any code (Vue or plain JS) can draw a wire by dispatching:

```js
document.dispatchEvent(new CustomEvent('connectnodes', {
    detail: {
        sender:   { label, direction: 'outbound', pipIndex },
        receiver: { label, direction: 'inbound',  pipIndex },
        line:     { color: '#aabbcc', width: 2 },  // optional
    }
}))
```

The canvas redraws lazily; call `dispatchRequestDrawEvent()` after if you need
an immediate paint.

## What to do next

- Add a new sub-app: load these three scripts first, then your own modules.
- If pip DOM ids change format, update `window.app.getTip` here — everything
  else derives pip positions from that function.
