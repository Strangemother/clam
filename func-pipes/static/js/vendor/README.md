# vendor/

Third-party and shared library files. Do not edit these for application logic —
wrap or guard in the app layer instead.

## Files

### `vue.global.prod.js`
Vue 3 production global build. Exposes `Vue` on `window`.
Load first — everything else depends on it.

### `dragsolo.js`
`DragSolo` class + `stickAll()` helper. Makes panels draggable by their header element.

Usage pattern (from each sub-app's HTML):
```js
stickAll()             // call after panels are rendered
new DragSolo(el, handle)
```

**Important behaviours to know:**
- `mousedown` on a pip element sets `draggable="true"` before the drag starts.
  This means `event.target.draggable` is `true` during a pip drag — the guard
  used in `pipes-runtime.js` relies on this.
- **Do not patch this file to fix input-focus conflicts.** Use a `@mousedown`
  guard in the template instead:
  ```html
  @mousedown="e => ['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName) && e.stopPropagation()"
  ```
  Put it on the panel body container div (not the header).

### `pipes-runtime.js`
Creates the canvas overlay system for drawing pip wires.

Key exported function: `createPipesRuntime(options)`

Returns: `{ walker, graph, canvasGroup }`

- `walker` — `PipesWalker`. Exposes `getOutgoingIds(panelId)` for signal forwarding
- `graph` — `Graph` instance (from `graph-runtime.js`)
- `canvasGroup` — `CanvasLayerGroup`. Manages the SVG/canvas overlay

Also exposes:
- `dispatchRequestDrawEvent()` — force a redraw of all wires
- `CanvasLayerGroup` class

Load after `vue.global.prod.js` and `dragsolo.js`.

### `graph-runtime.js`
Data structure backing the wiring graph.

Key classes:
- `Graph` — adjacency list. `addEdge(from, to)`, `removeEdge(from, to)`, `getEdges(id)`
- `GraphWalker` — traversal helpers
- `Stepper` — optional step-through debugger for wire propagation

Load before `pipes-runtime.js`.

### `chat.js`
`Chat` class. Wraps streaming LLM API calls.

```js
const c = new Chat({ endpoint, model, system })
c.onResponse = (chunk, done) => {}
c.send(text)        // appends to history, then calls the API
c.prompt(text)      // one-shot (no history kept)
```

- `_responseId` chains async responses so late-arriving chunks from an aborted
  call are ignored.
- `c.options.system` can be updated at any time — takes effect on the next call.
- Call `c.abort()` to cancel an in-flight request (sets an abort flag internally).

Used by: `prompting/prompt-llm.js` — created lazily via `_getLLMChat(panel)`.

### `model-list.js`
`ModelList` class. Fetches available model IDs from an LLM API endpoint.

```js
const ml = new ModelList({ endpoint })
ml.onResult = (ids) => {}
ml.getList()   // triggers fetch, calls onResult with array of model ID strings
ml.getIds()    // returns last fetched IDs synchronously
```

Used by: `prompting/prompt-llm.js` — `fetchModels()` creates a one-shot instance.

## Load order

Every HTML template must load vendors in this order:

```html
<script src="/static/js/vendor/vue.global.prod.js"></script>
<script src="/static/js/vendor/dragsolo.js"></script>
<!-- sub-app specific vendor additions: -->
<script src="/static/js/vendor/chat.js"></script>
<script src="/static/js/vendor/model-list.js"></script>
<script src="/static/js/vendor/pipes-runtime.js"></script>
<script src="/static/js/vendor/graph-runtime.js"></script>
```

Then `pipes/pipes-init.js`, then sub-app files, then `index.js` last.

## Updating a vendor file

Replace the file wholesale and verify:
1. The public API surface (constructor signature, method names) hasn't changed.
2. `stickAll()` still exists in `dragsolo.js`.
3. `createPipesRuntime` still exists in `pipes-runtime.js`.
4. Run the app and check the browser console before committing.
