"""Run a two-node Python graph and publish its results to Func Sockets.

This example exists for the README quick start. It connects to the ``demo``
graph room, executes ``source -> multiply``, and emits observable messages for
both node results.

Run from the ``func-sockets`` directory::

    python examples/demo_graph.py
"""

import argparse
import asyncio
import json
from functools import partial

from func_sockets import GraphSocket
from simple_bridge import FunctionNode, SimpleBridge, node_multiply, node_passthrough


async def run_demo(
    graph_id: str,
    value: int,
    multiplier: int,
    wait_for_message: bool = True,
) -> None:
    """Execute the graph, publish results, and optionally receive one UI message."""
    bridge = SimpleBridge()
    bridge.register_node(FunctionNode("source", node_passthrough))
    bridge.register_node(
        FunctionNode("multiply", partial(node_multiply, multiplier=multiplier))
    )
    bridge.easy_connect_pips("source", "multiply")

    async with GraphSocket(graph_id) as socket:
        await socket.send(
            {
                "kind": "event",
                "name": "graph.started",
                "graph_id": graph_id,
                "payload": {"input": value, "multiplier": multiplier},
            }
        )

        async def forward_result(event) -> None:
            node = event.payload["node"]
            await socket.send(
                {
                    "kind": "event",
                    "name": "node.output_emitted",
                    "graph_id": graph_id,
                    "payload": {
                        "node_id": node.node_id,
                        "pip": node.pip,
                        "value": event.payload["value"],
                    },
                }
            )

        bridge.on(SimpleBridge.NODE_RESULT, forward_result)
        bridge.enqueue_node_call("source", value)
        processed = await bridge.call_waiting_events()

        await socket.send(
            {
                "kind": "event",
                "name": "graph.idle",
                "graph_id": graph_id,
                "payload": {"processed_events": processed},
            }
        )

        if wait_for_message:
            print("graph finished; waiting for one message from the UI...")
            incoming = await socket.receive()
            if isinstance(incoming, bytes):
                incoming = incoming.decode("utf-8", errors="replace")
            try:
                decoded = json.loads(incoming)
            except json.JSONDecodeError:
                decoded = incoming
            print(f"received from UI: {decoded}")
            await socket.send(
                {
                    "kind": "event",
                    "name": "demo.command_received",
                    "graph_id": graph_id,
                    "payload": {"message": decoded},
                }
            )

    print(f"demo graph {graph_id!r}: {value} -> {value * multiplier}")


def main() -> None:
    """Read optional demo settings and run the graph once."""
    parser = argparse.ArgumentParser(description="Run a graph and publish its node events")
    parser.add_argument("--graph-id", default="demo")
    parser.add_argument("--value", default=3, type=int)
    parser.add_argument("--multiplier", default=4, type=int)
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Exit after publishing node events instead of waiting for a UI message",
    )
    args = parser.parse_args()
    asyncio.run(
        run_demo(
            args.graph_id,
            args.value,
            args.multiplier,
            wait_for_message=not args.no_wait,
        )
    )


if __name__ == "__main__":
    main()