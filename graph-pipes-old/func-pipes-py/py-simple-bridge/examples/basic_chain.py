import asyncio
from functools import partial

from simple_bridge import FunctionNode, SimpleBridge, node_multiply, node_passthrough


async def main() -> None:
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("start", node_passthrough))
    bridge.register_node(FunctionNode("mult", partial(node_multiply, multiplier=4)))
    bridge.easy_connect_pips("start", "mult")

    def show_result(event) -> None:
        node = event.payload["node"]
        print(f"{node.node_id}: {event.payload['value']}")

    bridge.on(SimpleBridge.NODE_RESULT, show_result)
    bridge.enqueue_node_call("start", 3)
    await bridge.call_waiting_events()


if __name__ == "__main__":
    asyncio.run(main())
