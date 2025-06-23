"""A Client connects to the "primary" as a message unit.
It can send and receive messages as a client.

In this version it should connect with 'Abilities', and be packaged into the
cluster graph.
"""

import asyncio
from websockets.asyncio.client import connect
import websockets

async def main():
    """Serve.
    """
    pair = ("localhost", 8765)
    print('Waking Service. on', pair)
    uri = "ws://localhost:8765"
    params = {
        "user_agent_header": "websockets/client.1",
        "open_timeout": 2.0,
    }
    # https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html#opening-a-connection
    async for websocket in connect(uri, **params):
        print('Connected', pair)
        res = await client_connected(websocket)
        if res is False:
            print('Shutting down')
            return


async def client_connected(websocket):

    print('Sending first message')
    await websocket.send('{ "uuid": 100 }')

    try:
        print('waiting on messages')
        async for message in websocket:
            await process_message(message, websocket)
    except websockets.exceptions.ConnectionClosed:
        print('Socket closed')
        # websocket.send('{ "id": 100 }')
    return False


async def process_message(message, websocket):
    print('Process message', message)



if __name__ == "__main__":
    asyncio.run(main())