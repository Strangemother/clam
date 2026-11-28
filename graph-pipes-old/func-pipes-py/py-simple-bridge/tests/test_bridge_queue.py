from functools import partial

import pytest

from simple_bridge import (
    FunctionNode,
    NodeOutput,
    SimpleBridge,
    node_multiply,
    node_passthrough,
)


@pytest.mark.asyncio
async def test_manual_pump_runs_a_simple_chain() -> None:
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("start", node_passthrough))
    bridge.register_node(FunctionNode("mult", partial(node_multiply, multiplier=4)))
    bridge.easy_connect_pips("start", "mult")

    results: list[tuple[str, int]] = []

    def capture(event) -> None:
        node = event.payload["node"]
        results.append((node.node_id, event.payload["value"]))

    bridge.on(SimpleBridge.NODE_RESULT, capture)
    bridge.enqueue_node_call("start", 3)

    processed = await bridge.call_waiting_events()

    assert processed == 4
    assert bridge.waiting_count == 0
    assert results == [("start", 3), ("mult", 12)]


@pytest.mark.asyncio
async def test_named_pips_route_without_in_out_defaults() -> None:
    class EmitterNode:
        node_id = "node_a"

        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def graph_execute(self, value: str, pip: str = "in") -> NodeOutput:
            self.calls.append((pip, value))
            return NodeOutput(value=f"{value}:{pip}", pip="foo")

    class ReceiverNode:
        node_id = "node_b"

        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def graph_execute(self, value: str, pip: str = "in") -> str:
            self.calls.append((pip, value))
            return f"done:{pip}:{value}"

    bridge = SimpleBridge()
    emitter = bridge.register_node(EmitterNode())
    receiver = bridge.register_node(ReceiverNode())
    bridge.connect_pips(("node_a", "foo"), ("node_b", "bar"))

    results: list[tuple[str, str, str]] = []

    def capture(event) -> None:
        node = event.payload["node"]
        results.append((node.node_id, node.pip, event.payload["value"]))

    bridge.on(SimpleBridge.NODE_RESULT, capture)
    bridge.enqueue_node_call(("node_a", "trigger"), "seed")

    processed = await bridge.call_waiting_events()

    assert processed == 4
    assert emitter.calls == [("trigger", "seed")]
    assert receiver.calls == [("bar", "seed:trigger")]
    assert results == [
        ("node_a", "foo", "seed:trigger"),
        ("node_b", "out", "done:bar:seed:trigger"),
    ]