# prompting/

LLM text pipeline. Wire text-input nodes through transform chains into LLM Chat
nodes, display results, and pipe outputs onward.

Route: `/prompting`

## Signal format

```js
{ text: string, meta?: { role: string, model: string } }
null   // no signal / gate blocked
```

## Node types

| Type | Pips | Description |
|------|------|-------------|
| `text-input` | → out | Manual text entry. Send via the panel button |
| `llm` | in, system → out | Chat node backed by `Chat` class. `in` receives user messages; `system` overrides the system prompt |
| `text-display` | in → out | Sink + passthrough. Renders received text, forwards unchanged |
| `transform` | N in → M out | Text fn + gate. Named in/out pips, user-editable JS, 15 presets |

## LLM node (`prompt-llm.js` + `prompt-signal.js`)

The `in` pip (index 0) queues text through a `Chat` instance (`panel._chat`).
The `system` pip (index 1) directly sets `panel._chat.options.system` without
queuing a chat turn.

`panel._chat` is a `Chat` instance from `vendor/chat.js`. It is created in
`_getLLMChat(panel)` and reused between calls. The response streams via
`_chat.onResponse = (chunk, done) => {...}`.

## LLM panel fields

| Field | Type | Notes |
|-------|------|-------|
| `_manualInput` | string | Bound to the manual text input in the panel. NOT a signal field |
| `promptPath` | string \| null | Path to a loaded system prompt file |
| `modelId` | string | Currently selected model ID |
| `streaming` | boolean | True while a response is in progress |
| `lastOutput` | string | Last complete response text |

## Transform node (`prompt-transform.js`)

Function body is evaluated with `new Function()`:

```js
fn(text, name, inputs) → string | { pipName: string } | null
```

- `text` — value on the pip that changed
- `name` — pip name string
- `inputs` — snapshot of all inbound pip values `{ name: text }`
- Return a string to emit on all outbound pips
- Return a named object `{ pipName: '...' }` to route to a specific pip
- Return `null` to suppress propagation

Gate modes: `'truthy'` (non-empty string), `'matches'` (regex against `gatePattern`), `'always'`

`TRANSFORM_PRESETS` in `prompt-transform.js` — 15 entries, selected via dropdown.

## Method groups

| File | Exported as | Responsibility |
|------|-------------|----------------|
| `nodes.js` | factories, `COMPONENT_CATALOG` | Panel factories, `PROMPTING_API_BASE`, `DEFAULT_ENDPOINT` |
| `prompt-spawn.js` | `SpawnMethods` | Add, remove, reset panels |
| `prompt-signal.js` | `SignalMethods` | Route `{text}` signals, `inPipIndex` threading, `_combineSources` |
| `prompt-llm.js` | `LLMMethods` | Chat lifecycle, `fetchModels`, `fetchPrompts`, `selectPrompt`, `sendTextInput`, `sendLLMManual` |
| `prompt-transform.js` | `TransformMethods` | Gate eval, `new Function()` eval, preset management, add/remove pips |
| `prompt-wiring.js` | `WiringMethods` | Pip drag-drop, connect (wire color `#cc88ff`), disconnect |
| `prompt-persist.js` | `PersistMethods` | Save/load/export; LLM nodes reload `promptPath` via `selectPrompt` on restore |

## `data()` keys (index.js)

| Key | Default | Notes |
|-----|---------|-------|
| `modelsEndpoint` | `DEFAULT_ENDPOINT` | Editable in toolbar. Manual fetch only — NOT called on mount |
| `modelIds` | `[]` | Populated by `fetchModels()` |
| `prompts` | `[]` | Loaded from Flask `/prompting/prompts/` on mount |
| `disconnectMode` | false | Two-click disconnect toggle |
| `transformPresets` | `TRANSFORM_PRESETS` | Drives preset dropdown |

## Flask backend (`prompting.py`)

| Route | Purpose |
|-------|---------|
| `GET /prompting/` | Serves `prompting.html` |
| `GET /prompting/prompts/` | Lists `.txt`/`.md` files from `PROMPTS_DIR` |
| `GET /prompting/prompts/<path>` | Returns a single prompt file's raw content |
| `POST /prompting/prompts/render` | Renders a prompt with variable substitution |

`PROMPTS_DIR` defaults to `../v5_2/prompts` or the `PROMPTS_DIR` env var.

## Vue 3 rule — critical

Template expressions **cannot access methods whose names start with `_`**.
All methods called from the template (button handlers, etc.) must have names
without a leading underscore. Internal helpers can use `_prefix` freely.

## Model endpoint

`modelsEndpoint` is a plain data string, editable via the toolbar input.
`fetchModels()` reads `this.modelsEndpoint`. It is **not** called automatically
on mount — click the `⟳ Models` button in the toolbar to load.

## Things to watch

- `sendTextInput` and `sendLLMManual` have no `_` prefix — intentional Vue 3 requirement.
- `panel._chat` is created lazily in `_getLLMChat`. Do not call `_applyLLM`
  before the panel is fully initialised.
- `stopLLM(panel)` calls `panel._chat.abort()` if the chat supports it.
- After `loadLayout` / `importJSON`, LLM nodes call `selectPrompt(panel,
  panel.promptPath)` to reload the system prompt from the server.
- DragSolo guard in `prompting.html`:
  `@mousedown="e => ['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName) && e.stopPropagation()"`
  — on every panel body container. Do not remove it or inputs become un-focusable.
