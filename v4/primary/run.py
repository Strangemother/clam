"""The proxy handles comms to/from the ui and bots.

Boot the proxy in parallel to the server. The user connects to the server -
communicating to the bot through the socket.

"""
import asyncio
from websockets.asyncio.server import serve
import websockets
import json

import cluster
from clients import set_register, drop_register

from loguru import logger

log = logger.debug


from uuid import uuid4

def str_uuid4():
    return str(uuid4())


async def main():
    """Serve.
    """
    pair = ("localhost", 8765)
    log(f'Waking Service. on {pair=}')
    # The capture function receives the new socket
    async with serve(capture, *pair) as server:
        log(f'Served {pair=}')
        await server.serve_forever()


async def send_json(websocket, **kw):
    return await websocket.send(json.dumps(kw))


async def capture(websocket):
    """ Called by `asyncio.server.serve` for a new socket.

        Onboard the socket and start receiving messages.
        Send all incoming messages to the recv_message().

        Return nothing.
    """
    await onboard(websocket)

    # Async now waits forever
    async for message in websocket:
        # Hooking when a new message appears
        try:
            await recv_message(websocket, message)
            await asyncio.sleep(.01)
        except websockets.exceptions.ConnectionClosed:
            log('Socket closed')

    # And now dropped when closed.
    log(f'Lost client {websocket.uuid=}')
    if websocket.registered is True:
        drop_register(websocket.uuid)
    return await cluster.drop_socket(websocket)


async def onboard(websocket):
    """ Called by `capture` on first connection.
    """
    log(f'onboard Socket {websocket=}')
    websocket.count = 0
    # Set to blank. The UUID Is applied elsewhere.
    websocket.uuid = -1
    websocket.registered = False
    websocket.receipts = True


async def recv_message(websocket, message):
    """
    Receive the message from the given websocket - expecting JSON from the client.

    If the socket is new, expect a UUID message - it registers and calls
    cluster.new_socket. After the first call, all salls are sent to
    cluster.recv_message().
    """
    if len(message) > 0 and message[0] == "{":
        d = json.loads(message)
    else:
        # log('binary or string message')
        d = {
            'raw': message
        }
    if websocket.count == 0 or websocket.uuid == -1:
        log('Detected new socket')
        return await recv_new_socket(websocket, d)

    # log(f'Recv {message=}')
    websocket.count += 1
    origin_id = str_uuid4()

    # send acceptance.
    if websocket.receipts is True:
        receipt = {
                'ok':True,
                'code':1111,
                'accept':len(message),
                'origin_id':origin_id,
            }
        if '_meta' in d:
            receipt['_meta'] = d['_meta']
        await send_json(websocket, **receipt)

    if 'origin_id' in d:
        # d['origin_id'] = d['origin_id']
        # log(' - origin_id exists')
        pass
    else:
        d['origin_id'] = origin_id

    # send to cluster.
    await cluster.recv_message(websocket, d)


async def recv_new_socket(websocket, d):
    """Called by the `recv_message` function when it detects a newly incoming
    socket.

    Called _once_ per socket, first time.

    Check the socket for authenticity, then onboard the socket to the register.
    Finally. Inform the socket of the acceptance, and hand-off to the cluster
    _new socket_ process.

    """
    # No messages ever. Start the register.
    uuid = d['uuid']

    if not accepted(websocket, d):
        log(f'Refuse client: {uuid=}')
        # https://github.com/Luka967/websocket-close-codes
        return await websocket.close(4001, reason='failed ID')
    # Store in the persistent.
    set_register(uuid, websocket)
    log(f'Recv {uuid=}')
    websocket.registered = True
    # setup the new socket.
    websocket.uuid = uuid
    websocket.count += 1
    await send_json(websocket, ok=True, code=1111, accept=uuid)
    # tell the _cluster_ it has an active input.
    return await cluster.new_socket(websocket, d)


def accepted(websocket, data):

    return 'role' in data


if __name__ == "__main__":
    asyncio.run(main())