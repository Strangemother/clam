# Func Sockets

A standalone development WebSocket relay for Func Pipes graphs. It groups
connections by graph ID and forwards messages between peers in the same graph.
It does not execute graphs, inspect application messages, persist events, or
depend on the Func Pipes application.


For a developer-oriented explanation of every source file and where changes
belong, see [docs/file-guide.md](docs/file-guide.md). Public functions and
methods also include minimal examples in their docstrings or JSDoc.

## Quick start

[Install](#install-and-run) below first. Then, from the `func-sockets` directory,
use three terminals.

After installing, run the relay service in a terminal:

```bash
func-sockets
# func-sockets: bind by URL: ws://0.0.0.0:8777/graph/<graph_id>
# websockets.server: server listening on 0.0.0.0:8777
```

Run the browser spy in another terminal:

```bash
python examples/spy/run.py
# Socket spy: http://127.0.0.1:8000/
```

Head to http://127.0.0.1:8000/

In another terminal, run the graph:

```bash
python examples/demo_graph.py
```

The monitor shows:

```text
graph.started
node.output_emitted (source = 3)
node.output_emitted (multiply = 12)
graph.idle
```

Click **Send** in the monitor. Terminal 3 receives the message, replies with
`demo.command_received`, and exits.

## Responsibilities

The service does only three things:

1. Bind each connection to one graph ID.
2. Keep graph rooms isolated from one another.
3. Relay text and binary messages unchanged to the other clients in that room.

The sender does not receive its own message. A room and its graph ID disappear
from relay memory when the final client disconnects. The relay stores no graph
state and does not replay messages.

## Install and run

```bash
cd /workspaces/clam/func-sockets
python -m pip install -e .[dev]
```

run as a standalone service:

```bash
func-sockets
```

The default address is `ws://0.0.0.0:8777`. Override it when needed:

```bash
func-sockets --host 127.0.0.1 --port 8777 --log-level DEBUG
```

You can also run `python -m func_sockets` from this directory.

## Bind by URL

The preferred form is:

```text
ws://127.0.0.1:8777/graph/<graph_id>
```

These forms are also accepted:

```text
ws://127.0.0.1:8777/graphs/<graph_id>
ws://127.0.0.1:8777/<graph_id>
ws://127.0.0.1:8777/?graph_id=<graph_id>
```

The server confirms binding:

```json
{"type": "bound", "graph_id": "graph-42"}
```

## Bind by message

Connect to `ws://127.0.0.1:8777/` and send:

```json
{"type": "bind", "graph_id": "graph-42"}
```

The same connection can send another bind message to move to another graph.
Bind messages are relay control messages and are not forwarded to peers.

Sending application traffic before binding returns:

```json
{"type": "error", "message": "bind to a graph before sending messages"}
```

## Application messages

After binding, every message other than `type: bind` is opaque relay traffic.
The service does not require the Func Pipes command/event schema:

```json
{
  "kind": "event",
  "name": "node.output_emitted",
  "graph_id": "graph-42",
  "payload": {"node_id": "multiply-1", "pip": "result", "value": 20}
}
```

The envelope's `graph_id` is application data. Routing uses the graph to which
the connection is bound, preventing a payload from selecting another room.

## Python graph client

`src/func_sockets/graph_socket.py` supplies a minimal async adapter:

```python
from func_sockets import GraphSocket


async with GraphSocket("graph-42") as socket:
    await socket.send({"kind": "event", "name": "graph.idle"})
```

The graph can keep this connection open and publish every observable domain
event. It may also receive UI commands over the same connection.

## Browser client

Load `examples/spy/graph-socket.js`, then connect the UI projection:

```javascript
const socket = new GraphSocket('graph-42')
socket.addEventListener('message', (event) => {
    graphStore.apply(event.detail)
})
socket.connect()
```

Use `socket.send(command)` for UI-to-graph commands. The relay sends that
command to every other peer in `graph-42`; the Python graph process decides
whether it is a command intended for it.

`examples/spy/` is the manual browser client and includes its own HTTP runner.
`examples/publisher.py` publishes one test message from Python.

## Test

```bash
cd /workspaces/clam/func-sockets
python -m pytest -q
```

## Development limitations

- No authentication, authorization, TLS, or origin checks.
- No graph ownership or graph process discovery.
- No retained messages, snapshots, acknowledgements, or persistence.
- No guarantee that a graph process is connected to a room.
- No cross-process relay state; run one relay instance.
- No application-level delivery guarantee beyond the live socket send.

Those concerns belong in later infrastructure or in the graph command/event
protocol. This process intentionally remains a small transport bridge.
