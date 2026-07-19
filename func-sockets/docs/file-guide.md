# File Guide

This guide answers two questions: why each source file exists and when you are
expected to use or change it. Function-level examples live beside the functions
as Python docstrings or JavaScript JSDoc.

## Runtime files

### `relay.py`

This is the transport-independent routing core. It remembers which socket is
bound to which graph and forwards messages to the other sockets in that graph.

Open this file when changing:

- Accepted graph URL formats.
- Bind-message behavior.
- Room membership or forwarding behavior.
- Sender echo or failed-client handling.

Do not add graph commands, node execution, snapshots, or UI rules here. The
relay intentionally treats application traffic as opaque text or bytes.

Minimal direct use:

```python
relay = GraphRelay()
relay.bind(graph_socket, "demo")
relay.bind(ui_socket, "demo")
await relay.receive(graph_socket, "graph event")
```

### `server.py`

This is the executable network adapter. It opens port `8777`, creates one
`GraphRelay`, and feeds real WebSocket connections into it.

Open this file when changing:

- Command-line host, port, or logging options.
- WebSocket server configuration.
- Connection startup and cleanup.

Run it with:

```bash
python server.py --host 0.0.0.0 --port 8777
```

Application graph behavior does not belong here. This file should remain a
thin adapter around `GraphRelay`.

## Client files

### `clients/graph_socket.py`

This is the reusable Python-side connection. The future graph process should
use it to publish backend events and receive UI commands.

Minimal use:

```python
from clients import GraphSocket


async with GraphSocket("demo") as socket:
    await socket.send({"kind": "event", "name": "graph.idle"})
    command = await socket.receive()
```

Open this file when changing Python connection behavior such as decoding,
reconnection, or bind confirmation. Graph command handling belongs in the
graph application, not in this client.

### `clients/graph-socket.js`

This is the browser-side equivalent. The UI uses it to send commands and
receive events. Incoming JSON is available through a `message` event's
`detail` property.

Minimal use:

```javascript
const socket = new GraphSocket('demo')
socket.addEventListener('message', (event) => {
    console.log(event.detail)
})
socket.addEventListener('open', () => {
    socket.send({ kind: 'command', name: 'graph.snapshot.get' })
})
socket.connect()
```

Open this file when changing browser connection mechanics. Vue components and
graph projection state belong in the UI application.

## Examples

### `examples/demo_graph.py`

This is the complete end-to-end exercise used by the README quick start. It
creates a real `source -> multiply` Python graph, forwards each node result to
the `demo` socket room, waits for one browser command, replies, and exits.

Run it after connecting the browser monitor to the `demo` room:

```bash
python examples/demo_graph.py
```

Use `--value` and `--multiplier` to change the calculation, or `--no-wait` to
publish graph events without waiting for a browser message.

### `examples/publisher.py`

This is a one-shot smoke-test publisher. It connects, sends one message, and
exits. Because the relay does not retain messages, another client must already
be connected to observe it.

```bash
python examples/publisher.py demo '{"name":"graph.idle"}'
```

Use `GraphSocket` directly for a long-running graph process.

### `examples/browser.html`

This is a manual browser test page. It can connect to a graph, display incoming
messages, and send text or JSON. It is not the intended Func Pipes UI.

Serve the project directory so the browser can load its JavaScript dependency:

```bash
cd /workspaces/clam/func-sockets
python -m http.server 8080
```

Then open `http://127.0.0.1:8080/examples/browser.html`.

## Project and test files

### `pyproject.toml`

Defines the Python package, its `websockets` dependency, development test
dependencies, and the installed `func-sockets` command. Change it when adding a
runtime dependency or packaging another Python module.

### `tests/test_relay.py`

Tests room binding, rebinding, URL parsing, raw forwarding, and isolation
without opening a network port.

### `tests/test_server.py`

Opens a real temporary WebSocket server and proves that messages cross a live
socket only within their selected graph.

Run every test with:

```bash
python -m pytest -q
```
