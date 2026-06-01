import asyncio

from simple_bridge import NodeOutput, SimpleBridge


class CustomEntryNode:
    node_id = "node_a"

    async def graph_execute(self, value: str, pip: str = "in") -> NodeOutput:
        print(f"node_a received via {pip}: {value}")
        return NodeOutput(value=f"{value}:{pip}", pip="alpha")


class CustomMiddleNode:
    node_id = "node_b"

    async def graph_execute(self, value: str, pip: str = "in") -> NodeOutput:
        print(f"node_b received via {pip}: {value}")
        return NodeOutput(value=f"{value}:{pip}", pip="gamma")


class CustomExitNode:
    node_id = "node_c"

    async def graph_execute(self, value: str, pip: str = "in") -> NodeOutput:
        print(f"node_c received via {pip}: {value}")
        return NodeOutput(value=f"done:{pip}:{value}", pip="result")


async def main() -> None:
    bridge = SimpleBridge()
    bridge.register_node(CustomEntryNode())
    bridge.register_node(CustomMiddleNode())
    bridge.register_node(CustomExitNode())

    bridge.connect_pips(("node_a", "alpha"), ("node_b", "beta"))
    bridge.connect_pips(("node_b", "gamma"), ("node_c", "delta"))

    def show_result(event) -> None:
        node = event.payload["node"]
        print(f"emitted from {node.node_id}:{node.pip} -> {event.payload['value']}")

    bridge.on(SimpleBridge.NODE_RESULT, show_result)
    bridge.enqueue_node_call(("node_a", "entry"), "seed")

    await bridge.call_waiting_events()


if __name__ == "__main__":
    asyncio.run(main())