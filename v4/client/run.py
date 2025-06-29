"""A Client connects to the "primary" as a message unit.
It can send and receive messages as a client.

In this version it should connect with 'Abilities', and be packaged into the
cluster graph.
"""

from collections import defaultdict
import asyncio
from loguru import logger

warning = logger.warning
# from websockets.asyncio.client import connect
# import websockets

from http_tools import http_post_json, http_get_json
from client_tools import (
        connect_wait, send_json, print_bit, log,
        concat_stream_messages, start_message_stream, close_message_stream
    )
import client_tools

# import alpha_config as conf

from pydoc import locate
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("conf_name", help="config module name", nargs='?', default='alpha_config')
args = parser.parse_args()
print(' -- loading:', args.conf_name)
conf = locate(args.conf_name)
# A history of messages is stored against a session id.
# This is persistent for the life of the session
# and will be stored down later.

# def new_list():
#     print('new list')
#     return list()

histories = defaultdict(list)


async def main():
    """Serve - duck-punch the client tools, and start _waiting_
    Connect to the socket and wait for messages.
    """
    client_tools.process_data = process_data
    return await connect_wait(conf)


async def process_data(data, websocket):
    """A Message from the socket.

    Do the required work, posting to the service and pushing
    results through the socket.
    """
    # await asyncio.sleep(2)
    data['extra'] = 200

    print('-- ', data, '\n')
    routing = data.get('routing', 'message')

    if routing == 'command':
        return await process_command(data, websocket)
    return await process_message(data, websocket)


async def process_command(data, websocket):
    """A message with "routine=command" to perform tasks outside the
    messaging processing, such as meta requests from the system.
    """
    print('command message', data)
    origin_id = data.get('origin_id', 'no-origin-id')
    session_id = data.get('session_id', 'no-session-id')
    action = data.get('action')

    if action == 'get_models':
        model_message = {
            'result': {
                'tags': await get_tags(),
                'ps': await get_ps(),
            },
            'origin_id': origin_id,
            'session_id': session_id,
        }

        await send_json(websocket, model_message)

    if action == 'get_role':
        role_message = {
            'origin_id': origin_id,
            'session_id': session_id,
        }

        role_message.update({
            'result': conf.FIRST_MESSAGE
        })

        await send_json(websocket, role_message)

    if action == 'set_role':

        role_message = {
            'origin_id': origin_id,
            'session_id': session_id,
        }

        conf.FIRST_MESSAGE = data['first_message']
        print('Updating first_message', conf.FIRST_MESSAGE)
        role_message['ok'] = True

        session_id = data.get('session_id', None)
        if session_id:
            # The system role message (first one), needs altering.
            h = histories[session_id]
            print('Editing first message', session_id, len(h))
            if len(h) > 0:
                h[0] = conf.FIRST_MESSAGE

        await send_json(websocket, role_message)

    if action == 'set_model':
        # Set the model.
        resp_msg = {
            'origin_id': origin_id,
            'session_id': session_id,
        }

        model_name = data.get('model_name', conf.MODEL_NAME)
        print('Call to set model',  model_name)
        res = await set_model(model_name)
        conf.MODEL_NAME = res[0]['model']
        print('New model', conf.MODEL_NAME)
        resp_msg['ok'] = True
        resp_msg['result'] = res
        await send_json(websocket, resp_msg)


async def set_model(model_name):
    # If an empty prompt is provided, the model will be loaded into memory.

    # Request
    # curl http://localhost:11434/api/generate -d '{
    #   "model": "llama3.2"
    # }'
    url = conf.OLLOMA_GENERATE_ENDPOINT
    r = await http_post_json(url, {'model': model_name})
    print('set model response', r)
    return r

async def get_tags():
    url = conf.OLLOMA_TAGS_ENDPOINT
    log(f'Sending {url=}')
    return await http_get_json(url)


async def get_ps():
    url = conf.OLLOMA_PS_ENDPOINT
    log(f'Sending {url=}')
    return await http_get_json(url)


async def ping_open_model(model_name=None):
    model_name = conf.MODEL_NAME

    url = conf.OLLOMA_PS_ENDPOINT
    log(f'Sending {url=}')
    return await http_get_json(url)


async def process_message(data, websocket):
    role = 'user'
    model_name = conf.MODEL_NAME
    content = data.get('text', None)
    if content is None:
        print('No text in message', data)

    msg = dict(
        role=role,
        content=content,
    )

    session_id = data.get('session_id', None)

    user_history = []
    if session_id is None:
        print('No session ID for this.')
    else:
        user_history = histories[session_id]

    if len(user_history) == 0:
        user_history += [conf.FIRST_MESSAGE]
    messages = user_history + [msg]

    log(f' -- history messages {len(messages)=}')

    d = {
        "model": model_name,
        "messages": messages,
        'stream': True,
    }

    url = conf.OLLOMA_CHAT_ENDPOINT
    log(f'Sending {url=} \n {len(d)=}')

    streambit_cache = { 'i': 0}

    async def stream_print_bit(decoded, response):

        if streambit_cache['i'] == 0:
            # First message needs to be the
            # stream info.
            await send_json(websocket, {
                'result': {
                    'model_name': decoded['model']
                },
                'code':1519,
                'origin_id': origin_id
            })

        streambit_cache['i'] += 1

        if 'message' in decoded:
            bit = decoded['message']['content']

            await asyncio.sleep(.001)
            await websocket.send(bit)

            print(bit, end='', flush=True)

            if decoded['done'] is True:
                print(' -- ')
        else:
            warning('Response from the API during streaming does not contain a message')
            print(decoded)
            print('--')
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
    log(f'result: {len(all_messages)=}')
    res_obj = concat_stream_messages(all_messages)
    # Extract the assistant message, and store it into the message stack.
    histories[session_id] = messages  + [res_obj['message']]

    print(histories[session_id])
    await close_stream(websocket, {
                'origin_id': origin_id
            })

    await send_json(websocket, {
            'result':res_obj,
            'code':1517,
            'origin_id': origin_id
        })
    # return True


if __name__ == "__main__":
    asyncio.run(main())