import asyncio
from functools import partial

import pytest

from simple_bridge import FunctionNode, SimpleBridge, node_multiply, node_passthrough


@pytest.mark.asyncio
async def test_background_loop_drains_events() -> None:
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("start", node_passthrough))
    bridge.register_node(FunctionNode("mult", partial(node_multiply, multiplier=5)))
    bridge.easy_connect_pips("start", "mult")

    done = asyncio.Event()
    results: list[int] = []

    def capture(event) -> None:
        node = event.payload["node"]
        if node.node_id == "mult":
            results.append(event.payload["value"])
            done.set()

    bridge.on(SimpleBridge.NODE_RESULT, capture)

    await bridge.start(interval=0.01)
    bridge.enqueue_node_call("start", 2)

    await asyncio.wait_for(done.wait(), timeout=1.0)
    await bridge.stop()

    assert results == [10]
    assert bridge.waiting_count == 0
