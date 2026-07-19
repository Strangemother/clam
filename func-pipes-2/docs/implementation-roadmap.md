# Implementation Roadmap

## Strategy

Build the integration from the Python domain outward. Do not begin by making
Vue components call a WebSocket directly against the current bridge internals.
First define graph state and messages that can be tested without Flask, then
adapt those messages to WebSockets and finally replace browser execution.

## Phase 1: Authoritative graph model

Extend `py-simple-bridge` with serializable domain models:

- Stable graph, node, edge, and event IDs.
- Node-type descriptions and a trusted node registry.
- Node instances with declared inbound and outbound pips.
- Current pip values and node execution status.
- Graph revision and event sequence.
- `to_dict()` or equivalent snapshot serialization.

Define graph methods for spawn, remove, connect, disconnect, pip mutation, input
updates, and execution. Keep transport concerns out of this package.

Acceptance criteria:

- A unit test creates a graph entirely in Python from registered node types.
- A snapshot fully describes nodes, pips, edges, values, and runtime status.
- Invalid connections and pip edits leave state unchanged.
- Existing bridge execution tests continue to pass.

## Phase 2: Commands and domain events

Implement typed command parsing and dispatch around the graph. Convert each
successful mutation into one or more protocol events. Add structured command
rejections.

Route bridge execution events through the graph event bus. Nodes emit to the
graph; they never emit to a WebSocket.

Acceptance criteria:

- Protocol tests send dictionaries into a command dispatcher without Flask.
- Accepted commands advance revision as specified.
- Events include graph ID, sequence, revision, and causation ID.
- A failed command emits no partial state-change events.
- Node output both routes internally and appears as an observable event.

## Phase 3: Graph manager and application lifecycle

Add an application service that owns active graphs:

- Create graph.
- Find graph by ID.
- Attach and detach subscribers.
- Start and stop graph execution.
- Dispose or expire graphs under an explicit policy.

For the MVP, use an in-memory registry. Keep its interface suitable for later
persistence.

Acceptance criteria:

- Two graphs execute independently without event leakage.
- Disconnecting the last UI does not unexpectedly corrupt graph execution.
- Application shutdown stops graph tasks cleanly.

## Phase 4: WebSocket adapter

Choose one async-compatible server approach and expose the protocol. The
adapter should:

- Parse command envelopes.
- Dispatch them to the graph service.
- Send acknowledgements to the requesting client.
- Subscribe the connection to graph events.
- Send a snapshot on attach.
- Unsubscribe and clean up on disconnect.

Do not place command-specific graph mutations in WebSocket handlers.

Acceptance criteria:

- An integration test creates a graph, spawns nodes, connects them, executes a
  value, and observes ordered events over a socket.
- Malformed and rejected commands return structured errors.
- Clients attached to different graphs receive only their own events.
- Reconnect produces a complete current snapshot.

## Phase 5: Generic frontend projection

Add a browser transport client and a client-side graph store. Replace static
Python function-name spawning with node-type metadata fetched from Python.

Build a generic Vue node component that renders:

- Node label and execution status.
- Declared inbound and outbound pips.
- Current values and errors.
- Optional controls selected from safe metadata hints.

Apply Python events to the store; Vue should render the store rather than call
domain node callbacks.

Acceptance criteria:

- Attaching to a graph renders its snapshot.
- `node.spawned` creates a panel with Python-declared pips.
- Value and execution events update the correct panel.
- Refreshing the page reconstructs the graph from Python.

## Phase 6: Move graph editing to commands

Convert existing UI actions:

- Spawn sends `node.spawn`.
- Connect sends `edge.connect`.
- Disconnect sends `edge.disconnect`.
- Pip controls send pip commands.
- Step sends `graph.step`.
- Editable values send `node.input.set`.

The UI may show a pending state identified by `request_id`, but it commits
authoritative state only from server acknowledgement and events.

Acceptance criteria:

- No topology mutation exists only in JavaScript.
- Rejected commands visibly restore or preserve authoritative state.
- Pip rename and removal update connected edges according to policy.
- Two attached clients converge on the same graph state.

## Phase 7: Retire duplicate browser execution

Remove or disable graph execution from `static/js/prompting/simple-bridge.js`
and node `customCallback()` paths. Retain only presentation and interaction
helpers that remain useful.

Acceptance criteria:

- Domain node functions run only in Python.
- Closing every browser does not prevent Python graph execution.
- Opening a second browser shows the same values and topology.
- The browser contains no second authoritative event queue.

## Later work

- Persistent graph storage and event history.
- Authentication and per-graph authorization.
- Event replay from a known sequence.
- Backpressure and bounded subscriber queues.
- Binary value codecs.
- Multiprocess graph workers.
- Node versioning and graph migrations.
- Undo/redo expressed as validated graph commands.

## Recommended first vertical slice

Keep the first end-to-end path deliberately small:

1. Register `passthrough` and `multiply` Python node types.
2. Create one in-memory graph through a command.
3. Attach one WebSocket client and receive its snapshot.
4. Spawn both nodes through commands.
5. Connect `passthrough:out` to `multiply:in`.
6. Send a value to `passthrough:in`.
7. Observe execution and output events in the browser.
8. Render both authoritative values with generic panels.

That slice proves graph ownership, command handling, transport, event delivery,
and dumb UI projection before adding editable dynamic pips or persistence.
