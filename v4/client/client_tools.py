
import json
import asyncio
from collections import defaultdict

from websockets.asyncio.client import connect
from loguru import logger
import websockets


log = logger.debug
warning = logger.warning


async def connect_wait(conf):
    """Given a config object, connect and wait on the websocket endpoint

        async def main():
            client_tools.process_data = process_data
            return await connect_wait(conf)

    """
    uri = conf.WEBSOCKET_ENDPOINT
    log(f'Waking Service. on {uri=}')
    params = {
        "user_agent_header": "websockets/client.1",
        "open_timeout": 2.0,
    }

    # https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html#opening-a-connection
    async for websocket in connect(uri, **params):
        log(f'Connected {uri=}')
        res = await client_connected(websocket, conf)
        if res is False:
            log('Shutting down')
            return


async def client_connected(websocket, conf):
    """The first function called after the connect occurs.

    Send the _confirmation_ message and wait for incoming messages.
    """

    log('Sending first message')
    await send_json(websocket, { "uuid": conf.UUID, "role": conf.ROLE })

    try:
        log('waiting on messages')
        async for message in websocket:
            unused = await process_message(message, websocket)
            if unused is not None:
                _type = type(unused)
                msg = f'client.process_message() return an unused {_type}.'
                warning(msg)
    except websockets.exceptions.ConnectionClosed:
        log('Socket closed')
        # websocket.send('{ "id": 100 }')
    return False


async def send_json(websocket, *a, **kw):
    r={}
    for d in a:
        r.update(d)
    r.update(kw)
    return await websocket.send(json.dumps(r))


async def process_message(message, websocket):
    """Caled by the message loop upon an incoming message.
    Convert the JSON message to a dictionary, and run `process_data`.

    If the message code is 1111 (is confirmation). process_data is not called.
    """
    log(f'Process message {message=}')
    data = json.loads(message)

    if is_confirmation(data):
        """A confirmation message is a cluster response,
        not a digestible.

        1111: Confirm last message
        1200: hello.
        """
        return True

    # Data is a task to perform.
    return await process_data(data, websocket)


async def process_data(data, websocket):
    pass


def print_bit(decoded, response):
    bit = decoded['message']['content']
    print(bit, end='', flush=True)

    if decoded['done'] is True:
        print(' -- ')


def is_confirmation(data):
    return data.get('code') in (1111, 1200)


def concat_stream_messages(all_messages):
    # Get the last object.
    # replace the message content with the stream result.
    res_obj = None
    content = ''
    for a_msg in all_messages:
        # Get the last one
        res_obj = a_msg
        m = a_msg['message'] if 'message' in a_msg else {}
        content += m.get('content', '')

    m = res_obj['message'] if 'message' in res_obj else {}
    m['content'] = content
    res_obj['message'] = m
    return res_obj


async def start_message_stream(websocket, data):
    """Tell the endpoint to expect many bits to fulfil the message content.
    """
    log('open stream request')
    d={}
    d['meta'] = data
    d['code'] = 1515
    d['text'] = 'open stream request'
    websocket.receipts = False
    await send_json(websocket, d)
    return close_message_stream


async def close_message_stream(websocket, data):
    log('close stream request')
    data['code'] = 1516
    data['text'] = 'close stream request'
    websocket.receipts = True
    await send_json(websocket, data)
