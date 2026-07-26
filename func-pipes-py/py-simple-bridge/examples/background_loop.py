import asyncio
from functools import partial

from simple_bridge import FunctionNode, SimpleBridge, node_multiply, node_passthrough


async def main() -> None:
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("start", node_passthrough))
    bridge.register_node(FunctionNode("mult", partial(node_multiply, multiplier=5)))
    bridge.easy_connect_pips("start", "mult")

    done = asyncio.Event()

    def show_result(event) -> None:
        node = event.payload["node"]
        if node.node_id == "mult":
            print(f"final: {event.payload['value']}")
            done.set()

    bridge.on(SimpleBridge.NODE_RESULT, show_result)

    await bridge.start(interval=0.01)
    bridge.enqueue_node_call("start", 2)

    await asyncio.wait_for(done.wait(), timeout=1.0)
    await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
