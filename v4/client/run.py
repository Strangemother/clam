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
    await send_json(websocket, { "uuid": 100, "role": "example" })

    try:
        print('waiting on messages')
        async for message in websocket:
            await process_message(message, websocket)
    except websockets.exceptions.ConnectionClosed:
        print('Socket closed')
        # websocket.send('{ "id": 100 }')
    return False


import json

async def send_json(websocket, *a, **kw):
    r={}
    for d in a:
        r.update(d)
    r.update(kw)
    return await websocket.send(json.dumps(r))


async def process_message(message, websocket):
    print('Process message', message)
    data = json.loads(message)

    if is_confirmation(data):
        return True

    return await process_data(data, websocket)


async def process_data(data, websocket):
    """Do the required work.
    """

    # await asyncio.sleep(2)
    data['extra'] = 200

    res = await post_generate(data, 'TinyDolphin')
    print('result:', type(res))
    await send_json(websocket, { 'result':res})
    return True

from http_tools import http_post_json
from collections import defaultdict

histories = defaultdict(tuple)

async def post_generate(data, model_name=None, role='user'):
    msg = dict(
        role=role,
        content=data['text'],
    )


    session_id = data.get('session_id', None)
    user_history = ()
    if session_id is None:
        print('No session ID for this.')
    else:
        user_history = histories[session_id]
    # msgs = self.messages + (msg, )
    # print('Sending', msg, f' as {role=} messages to', model_name)

    d = {
        "model": model_name,
        "messages": user_history + (msg,),
        'stream': True,
    }


    url = "http://192.168.50.60:10000/api/chat/"
    print('Sending', url, '\n', d)
    resp = await http_post_json(url, d, print_bit)
    histories[session_id] = histories[session_id] + (msg,)
    return resp



def print_bit(decoded, response):
    bit = decoded['message']['content']
    print(bit, end='', flush=True)

    if decoded['done'] is True:
        print(' -- ')


def is_confirmation(data):
    return data.get('code') == 1111


if __name__ == "__main__":
    asyncio.run(main())