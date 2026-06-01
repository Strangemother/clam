import asyncio
from functools import partial

from simple_bridge import FunctionNode, SimpleBridge, node_multiply, node_passthrough


async def main() -> None:
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("start", node_passthrough))
    bridge.register_node(FunctionNode("mult", partial(node_multiply, multiplier=3)))
    bridge.easy_connect_pips("start", "mult")

    def handle_demo_start(event) -> None:
        bridge.enqueue_node_call("start", event.payload["value"])

    def show_node_result(event) -> None:
        print(f"{event.payload['node'].node_id}: {event.payload['value']}")

    bridge.on("demo:start", handle_demo_start)
    bridge.on(SimpleBridge.NODE_RESULT, show_node_result)

    bridge.emit("demo:start", {"value": 4})
    await bridge.call_waiting_events()


if __name__ == "__main__":
    asyncio.run(main())
