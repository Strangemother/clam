# Func Pipes Architecture Notes

These documents define the intended direction for Func Pipes V2: a Python-owned
node executor graph with a browser UI that projects graph state and sends user
commands.

## Documents

1. [Current state](current-state.md) - what exists, what works, and what is not
   connected yet.
2. [Target architecture](target-architecture.md) - ownership boundaries,
   runtime flow, graph lifecycle, and design rules.
3. [Command and event protocol](command-event-protocol.md) - the shared message
   contract between clients and the Python graph.
4. [Implementation roadmap](implementation-roadmap.md) - a staged build plan
   with acceptance criteria.

## Core decision

Python is the authority for graph structure, execution, and runtime values. The
browser is a projection of that state. It may own presentation-only state such
as selection, viewport position, zoom, and temporary connection gestures.

The two sides communicate with commands and events:

```text
UI command -> transport -> Python graph
Python graph event -> transport -> UI projection
```

WebSockets are the expected first transport because communication is
bidirectional and long-lived. The graph itself must publish to an internal
event bus rather than depend directly on WebSockets.

## Vocabulary

- **Graph**: the authoritative collection of node instances, pips, edges, and
  runtime state.
- **Node type**: a reusable Python definition and its metadata schema.
- **Node instance**: one configured occurrence of a node type in a graph.
- **Pip**: a named inbound or outbound endpoint on a node.
- **Command**: a client request to mutate or execute a graph.
- **Event**: an authoritative statement that something happened in Python.
- **Snapshot**: a serializable representation used to initialize or restore a
  client projection.
- **Projection**: the UI's local rendering of authoritative Python state.
