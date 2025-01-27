"""The proxy handles comms to/from the ui and bots.

The frontend is a served websocket sevice.
"""
import asyncio
from websockets.asyncio.server import serve
import json
import cluster
from clients import set_register, drop_register


async def send_json(websocket, **kw):
    return await websocket.send(json.dumps(kw))


async def onboard(websocket):
    print('onboard Socket', websocket)
    websocket.count = 0

async def capture(websocket):
    await onboard(websocket)

    async for message in websocket:
        await recv_message(websocket, message)
    print('Lost client', websocket.uuid)
    drop_register(websocket.uuid)


async def recv_message(websocket, message):
    d = json.loads(message)
    if websocket.count == 0:
        uuid = d['uuid']
        set_register(uuid, websocket)
        print('Recv', uuid)
        websocket.uuid = uuid
        websocket.count += 1
        await send_json(websocket, ok=True, accept=uuid)
        return await cluster.new_socket(websocket, d)

    print('Recv', message)
    websocket.count += 1
    await send_json(websocket, ok=True, accept=len(message))
    # send to cluster.
    await cluster.recv_message(websocket, d)


async def main():
    pair = ("localhost", 8765)
    print('Waking Service. on', pair)
    async with serve(capture, *pair) as server:
        print('Served', pair)
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())