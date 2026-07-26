# py-simple-bridge

Minimal proof-of-concept Python port of the `simple-bridge.js` queue and
event flow.

## Scope

- Bridge-owned FIFO event queue
- Generic event intake via `emit()` / `push_event()`
- Manual queue pumping with `call_waiting_events()`
- Optional async background loop with `start()` / `stop()`
- Named inbound and outbound pips, with `in` and `out` only as defaults
- Small function-backed nodes for examples and tests

This PoC stays independent from Flask, DOM events, visual connection state,
and multiprocess transport.

## Layout

- `src/simple_bridge/bridge.py` - queue, dispatch, routing, async loop
- `src/simple_bridge/events.py` - lightweight pub/sub
- `src/simple_bridge/types.py` - event, edge, and pip dataclasses
- `src/simple_bridge/nodes.py` - minimal function-backed node adapter
- `examples/` - small runnable scenarios
- `tests/` - focused unit tests

## Install for development

```bash
cd /workspaces/clam/func-pipes-2/py-simple-bridge
python -m pip install -e .[dev]
```

## Run examples

```bash
cd /workspaces/clam/func-pipes-2/py-simple-bridge
python examples/basic_chain.py
python examples/custom_events.py
python examples/background_loop.py
python examples/named_pips.py
python examples/no_default_named_pips.py
```

## Run tests

```bash
cd /workspaces/clam/func-pipes-2/py-simple-bridge
pytest -q
```

## Minimal usage

```python
import asyncio
from functools import partial

from simple_bridge import FunctionNode, SimpleBridge, node_multiply


async def main() -> None:
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("mult", partial(node_multiply, multiplier=4)))
    bridge.enqueue_node_call("mult", 3)
    await bridge.call_waiting_events()


asyncio.run(main())
```

## Named pips

Any pip name can be used in a connection. For example:

```python
bridge.connect_pips(("node_a", "foo"), ("node_b", "bar"))
bridge.enqueue_node_call(("node_a", "trigger"), "seed")
```

Custom inbound pip names are passed through to `graph_execute(value, pip)`.
If a node needs to emit on a named outbound pip, return `NodeOutput`:

```python
from simple_bridge import NodeOutput


async def graph_execute(value, pip="in"):
    return NodeOutput(value=value, pip="foo")
```

Plain return values still emit through the default outbound pip `out`.
For a chain that uses only custom names and never relies on `in` or `out`, see
`examples/no_default_named_pips.py`.