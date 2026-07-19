"""Send one development message to a graph room and exit.

This is a command-line smoke-test client, not the long-running graph adapter.
Keep another client connected to the same graph to observe the message::

    python examples/publisher.py demo '{"name":"graph.idle"}'
"""

import argparse
import asyncio
import json

from func_sockets import GraphSocket


async def publish(graph_id: str, message: str) -> None:
    """Connect to ``graph_id``, send one message, and close.

    Example::

        await publish("demo", '{"name":"graph.idle"}')
    """
    async with GraphSocket(graph_id) as socket:
        await socket.send(message)
        print(f"sent to {graph_id}: {message}")


def main() -> None:
    """Read a graph ID and message from the command line, then publish it."""
    parser = argparse.ArgumentParser(description="Publish one graph relay message")
    parser.add_argument("graph_id")
    parser.add_argument("message", help="Text or JSON message")
    args = parser.parse_args()

    try:
        message = json.dumps(json.loads(args.message))
    except json.JSONDecodeError:
        message = args.message
    asyncio.run(publish(args.graph_id, message))


if __name__ == "__main__":
    main()
