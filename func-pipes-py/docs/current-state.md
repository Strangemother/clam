# Current State

## Summary

The repository contains two useful but independent graph implementations:

- `py-simple-bridge` is a tested Python event queue and node executor.
- `static/js/prompting/simple-bridge.js` is the graph currently used by the UI.

The Python implementation is a working executor foundation. The application
does not yet instantiate it, expose it through Flask, or forward its events to
the browser. The frontend therefore owns and executes the graph visible on
screen.

## Capability matrix

| Capability | Python | Browser | Integrated |
| --- | --- | --- | --- |
| Register node instances | Yes | Yes | No |
| Connect named pips | Yes | Yes | No |
| Queue and propagate results | Yes | Yes | No |
| Manual event pumping | Yes | Yes | No |
| Background event pumping | Yes | Partial timer loop | No |
| Add pips in the UI | No | Partial | No |
| Describe Python node pips to UI | No | N/A | No |
| Stream Python events to UI | Internal listeners only | N/A | No |
| Restore graph from Python snapshot | No | No | No |

## What is ready

The pure-Python bridge currently provides:

- A bridge-owned FIFO queue.
- Node registration and execution.
- Directed connections between named pips.
- Result propagation to downstream nodes.
- Default `in` and `out` pips.
- Explicit outbound selection with `NodeOutput`.
- Custom event listeners and global listeners.
- Node-error events.
- Manual draining and an async background pump.

Its focused test suite covers simple chains, named pips, custom events, errors,
connection order, and background execution.

## What the UI currently does

The browser can:

- Spawn Vue panels from statically registered component types.
- Add inbound and outbound pip objects locally.
- Draw and connect pips locally.
- Execute component callbacks through the JavaScript bridge.
- Store displayed values in local Vue state.
- Step the local JavaScript event queue.

This is more than a passive view: the browser currently performs graph
execution. That behavior must be retired or isolated when Python becomes the
authority.

## Missing integration

### Active Python runtime

The Flask application does not create a `SimpleBridge`, register graph nodes,
or manage graph sessions. Its `/nodes/` route returns only function names.

### Node metadata

A function name is not enough to generate a UI sibling. The browser needs a
serializable node-type description containing identity, labels, inbound pips,
outbound pips, defaults, value types, and optional view hints.

The current `FunctionNode` wraps a callable but does not expose this metadata.
It also calls the wrapped function with only the incoming value; the inbound
pip is not forwarded to that callable.

### Graph mutation API

UI pip additions and connections mutate JavaScript objects only. There are no
backend operations for spawning nodes, adding or renaming pips, connecting
edges, or changing input values.

The editable pip labels also have no binding that writes edited text back to
`pip.name`. Renaming would need to update or reject affected edges atomically.

### Bidirectional transport

There is no WebSocket, Server-Sent Events stream, or polling protocol for
Python graph events. The Python `EventEmitter` reaches callbacks in the same
process only.

### State synchronization

There is no graph snapshot, graph revision, event sequence, reconnect flow, or
shared serialization contract. A browser cannot reconstruct an already-running
Python graph.

## Behavioral difference to retain consciously

The JavaScript manual pump takes a snapshot of pending work and processes one
generation per call. Python's `call_waiting_events()` drains newly generated
work in the same call unless `max_events` is supplied. The server design should
choose explicit execution semantics rather than assuming these are identical.
