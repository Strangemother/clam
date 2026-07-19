import asyncio
import json

import pytest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from relay import GraphRelay
from server import handle_connection


@pytest.mark.asyncio
async def test_live_server_relays_within_one_graph_only() -> None:
    relay = GraphRelay()

    async def handler(websocket) -> None:
        await handle_connection(websocket, relay)

    async with serve(handler, "127.0.0.1", 0) as websocket_server:
        port = websocket_server.sockets[0].getsockname()[1]
        async with (
            connect(f"ws://127.0.0.1:{port}/graph/alpha") as source,
            connect(f"ws://127.0.0.1:{port}/graph/alpha") as same_graph,
            connect(f"ws://127.0.0.1:{port}/graph/beta") as other_graph,
        ):
            assert json.loads(await source.recv()) == {"type": "bound", "graph_id": "alpha"}
            assert json.loads(await same_graph.recv()) == {"type": "bound", "graph_id": "alpha"}
            assert json.loads(await other_graph.recv()) == {"type": "bound", "graph_id": "beta"}

            await source.send("hello alpha")

            assert await same_graph.recv() == "hello alpha"
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(other_graph.recv(), timeout=0.05)