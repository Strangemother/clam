import asyncio

from simple_bridge import NodeOutput, SimpleBridge


class NamedEmitter:
    node_id = "node_a"

    async def graph_execute(self, value: str, pip: str = "in") -> NodeOutput:
        print(f"node_a received via {pip}: {value}")
        return NodeOutput(value=f"{value}:{pip}", pip="foo")


class NamedRouter:
    node_id = "node_b"

    async def graph_execute(self, value: str, pip: str = "in") -> NodeOutput:
        print(f"node_b received via {pip}: {value}")
        return NodeOutput(value=f"{value}:{pip}", pip="baz")


class NamedSink:
    node_id = "node_c"

    async def graph_execute(self, value: str, pip: str = "in") -> str:
        print(f"node_c received via {pip}: {value}")
        return f"done:{pip}:{value}"


async def main() -> None:
    bridge = SimpleBridge()
    bridge.register_node(NamedEmitter())
    bridge.register_node(NamedRouter())
    bridge.register_node(NamedSink())

    bridge.connect_pips(("node_a", "foo"), ("node_b", "bar"))
    bridge.connect_pips(("node_b", "baz"), ("node_c", "qux"))

    def show_result(event) -> None:
        node = event.payload["node"]
        print(f"emitted from {node.node_id}:{node.pip} -> {event.payload['value']}")

    bridge.on(SimpleBridge.NODE_RESULT, show_result)
    bridge.enqueue_node_call(("node_a", "trigger"), "seed")

    await bridge.call_waiting_events()


if __name__ == "__main__":
    asyncio.run(main())