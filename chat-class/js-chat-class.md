# JS Chat Class — Requirements

A JavaScript class (`Chat`) that wraps a single LLM conversation lifecycle.
Multiple `Chat` instances can co-exist in one page, each independently managing
their own message history, state, and UI binding.

---

## Usage sketch

```js
const chat = new Chat({
    endpoint: '/v1/chat/completions/',
    model: 'llama3.2:latest',
    system: 'You are a helpful assistant.',
    stream: false,
})

// single prompt, no history
chat.prompt('What is the capital of France?')

// continuing conversation — history is kept automatically
chat.send('Tell me more.')

// bind to Vue reactive data
chat.on('response', (msg) => { vueData.reply = msg.content })
chat.on('update', (state) => { vueData.chatState = state })
```

---

## Constructor options (`ChatOptions`)

| Property | Type | Default | Description |
|---|---|---|---|
| `endpoint` | `string` | `'/v1/chat/completions/'` | URL to POST conversations to |
| `model` | `string` | `''` | Model name sent in every request |
| `system` | `string` | `''` | System prompt prepended as the first message in every request |
| `stream` | `boolean` | `false` | Whether to request streaming responses |
| `history` | `boolean` | `true` | Accumulate messages across calls; set `false` for single-shot mode |
| `maxHistory` | `number` | `0` | Trim history to last N message pairs; `0` = unlimited |
| `metadata` | `object` | `{}` | Arbitrary extra fields merged into every request body (e.g. `{ topic: 'conv' }`) |
| `pollInterval` | `number` | `500` | ms between polls when using async receipt-based responses |

---

## Properties

| Property | Type | Description |
|---|---|---|
| `messages` | `Array<Message>` | Full message history in OpenAI/Ollama format `[{role, content}]` |
| `state` | `'idle' \| 'pending' \| 'streaming' \| 'error'` | Current lifecycle state |
| `lastResponse` | `Message \| null` | Most recent assistant message object |
| `lastError` | `Error \| null` | Last caught error, `null` when clean |
| `options` | `ChatOptions` | Live reference to resolved options |

---

## Core methods

### `prompt(text)`
Send a one-shot user message **without** appending it to persistent history.
History is not modified before or after the call.
Returns a `Promise<Message>`.

```js
const reply = await chat.prompt('Summarise this in one sentence.')
```

### `send(text)`
Append `{ role: 'user', content: text }` to `messages`, POST the conversation,
append the assistant reply, and return a `Promise<Message>`.

```js
const reply = await chat.send('Hello')
```

### `reset(keepSystem = true)`
Clear `messages`. If `keepSystem` is `true` (default) the system message is
re-inserted so the next call still has context.

### `setSystem(text)`
Replace the system prompt. Takes effect on the next `send` / `prompt` call.

### `setModel(name)`
Update `options.model` in place.

### `buildPayload(userText?, role?)`
Returns the raw JSON object that would be POSTed for a given user text.
Useful for inspection or manual overrides before sending.

```js
const payload = chat.buildPayload('test')
// { model, messages: [...], stream, ...metadata }
```

### `on(event, handler)`
Register an event listener. Returns `this` for chaining.

### `off(event, handler)`
Remove a previously registered handler.

---

## Events

| Event | Payload | When |
|---|---|---|
| `'response'` | `Message` | A complete assistant reply has been received |
| `'chunk'` | `string` | A streaming token chunk arrived (only when `stream: true`) |
| `'update'` | `{ state, messages }` | `state` changed (idle → pending → idle, etc.) |
| `'error'` | `Error` | A network or parse error occurred |

---

## Message format

Mirrors the OpenAI chat-completions format used throughout the codebase:

```js
// outbound message object
{ role: 'user' | 'assistant' | 'system', content: string }

// full request body
{
    model: string,
    messages: Message[],
    stream: boolean,
    ...metadata          // merged from ChatOptions.metadata
}

// expected response shape (LM Studio / Ollama-compatible)
{
    id: string,
    created: number,
    choices: [{ message: { role: 'assistant', content: string } }]
}
```

---

## Vue integration

The class is framework-agnostic; bind via events and reactive data.

```js
// Vue 3 composition API example
const reply = ref('')
const status = ref('idle')

const chat = new Chat({ endpoint: '/v1/chat/completions/', model: 'llama3.2:latest' })
chat.on('response', (msg) => { reply.value = msg.content })
chat.on('update',   ({ state }) => { status.value = state })

async function sendMessage(text) {
    await chat.send(text)
}
```

```html
<!-- minimal Vue template for a single chat -->
<div>
    <p>Status: {{ status }}</p>
    <p>{{ reply }}</p>
    <input v-model="userInput" @keyup.enter="sendMessage(userInput)" />
</div>
```

Multiple chats on one page:

```js
const chatA = new Chat({ model: 'llama3.2:latest',  system: 'You are concise.' })
const chatB = new Chat({ model: 'granite-4.0-tiny', system: 'You are verbose.' })

chatA.on('response', (m) => { stateA.reply = m.content })
chatB.on('response', (m) => { stateB.reply = m.content })
```

---

## Polling / async receipt pattern

When the backend responds with a `receipt_id` instead of an immediate answer
(matching the existing `home.html` pattern), `Chat` detects the receipt and
polls `GET /result/<receipt_id>/` until a `message` key appears, then clears
it via `GET /clear/<receipt_id>/`.

This behaviour activates automatically when the POST response contains
`{ receipt_id }`. No extra configuration is needed.

---

## Error handling

- Network errors and non-2xx responses reject the returned Promise and fire the `'error'` event.
- `state` is set to `'error'`; `lastError` carries the error object.
- Callers may also `try/catch` around `send` / `prompt`.

---

## File placement suggestion

```
v5_2/
  clam/src/clam/
    static/js/
      chat.js        ← Chat class implementation
    templates/
      home.html      ← existing template (can import chat.js)
```
