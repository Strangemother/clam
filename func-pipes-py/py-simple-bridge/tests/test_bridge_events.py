from functools import partial

import pytest

from simple_bridge import FunctionNode, SimpleBridge, node_multiply, node_passthrough


@pytest.mark.asyncio
async def test_custom_events_can_trigger_bridge_work() -> None:
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("start", node_passthrough))
    bridge.register_node(FunctionNode("mult", partial(node_multiply, multiplier=3)))
    bridge.easy_connect_pips("start", "mult")

    seen_custom: list[int] = []
    results: list[tuple[str, int]] = []

    def kickoff(event) -> None:
        seen_custom.append(event.payload["value"])
        bridge.enqueue_node_call("start", event.payload["value"])

    def capture(event) -> None:
        node = event.payload["node"]
        results.append((node.node_id, event.payload["value"]))

    bridge.on("demo:start", kickoff)
    bridge.on(SimpleBridge.NODE_RESULT, capture)
    bridge.emit("demo:start", {"value": 4})

    await bridge.call_waiting_events()

    assert seen_custom == [4]
    assert results == [("start", 4), ("mult", 12)]


@pytest.mark.asyncio
async def test_node_failures_become_error_events() -> None:
    def boom(value):
        raise ValueError(f"bad value: {value}")

    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("explode", boom))

    errors: list[str] = []

    def capture(event) -> None:
        errors.append(event.payload["error"])

    bridge.on(SimpleBridge.NODE_ERROR, capture)
    bridge.enqueue_node_call("explode", 9)

    await bridge.call_waiting_events()

    assert errors == ["bad value: 9"]
    assert bridge.waiting_count == 0
