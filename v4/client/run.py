"""A Client connects to the "primary" as a message unit.
It can send and receive messages as a client.

In this version it should connect with 'Abilities', and be packaged into the
cluster graph.
"""

from collections import defaultdict
import asyncio
from loguru import logger
# from websockets.asyncio.client import connect
# import websockets

from http_tools import http_post_json
from client_tools import (
        connect_wait, send_json, print_bit, log,
        concat_stream_messages, start_message_stream, close_message_stream
    )
import client_tools

import alpha_config as conf


# A history of messages is stored against a session id.
# This is persistent for the life of the session
# and will be stored down later.
histories = defaultdict(tuple)


async def main():
    """Serve - duck-punch the client tools, and start _waiting_
    Connect to the socket and wait for messages.
    """
    client_tools.process_data = process_data
    return await connect_wait(conf)


async def process_data(data, websocket):
    """Do the required work, posting to the service and pushing
    results through the socket.
    """
    # await asyncio.sleep(2)
    data['extra'] = 200

    role = 'user'
    model_name = conf.MODEL_NAME

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

    d = {
        "model": model_name,
        "messages": user_history + (msg,),
        'stream': True,
    }

    url = conf.OLLOMA_CHAT_ENDPOINT
    log(f'Sending {url=} \n {d=}')

    async def stream_print_bit(decoded, response):
        bit = decoded['message']['content']
        await asyncio.sleep(.001)
        await websocket.send(bit)

        print(bit, end='', flush=True)

        if decoded['done'] is True:
            print(' -- ')

        # await send_json(websocket, {
        #         'bit':bit,
        #         'message': decoded['message'],
        #         'done': decoded['done'],
        #         'origin_id': data.get('origin_id', 'no-origin-id')
        #     })


    origin_id = data.get('origin_id', 'no-origin-id')
    close_stream = await start_message_stream(websocket, {
                'origin_id': origin_id
            })

    ## All messages are stacked after the response has ended.
    all_messages = await http_post_json(url, d, async_reader=stream_print_bit)

    histories[session_id] = histories[session_id] + (msg,)
    log(f'result: {len(all_messages)=}')
    res_obj = concat_stream_messages(all_messages)

    await close_stream(websocket, {
                'origin_id': origin_id
            })

    await send_json(websocket, {'result':res_obj, 'origin_id': origin_id})
    # return True


if __name__ == "__main__":
    asyncio.run(main())