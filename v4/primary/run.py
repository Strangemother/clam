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



async def main():
    """Serve.
    """
    pair = ("localhost", 8765)
    print('Waking Service. on', pair)
    # The capture function receives the new socket
    async with serve(capture, *pair) as server:
        print('Served', pair)
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
        except websockets.exceptions.ConnectionClosed:
            print('Socket closed')

    # And now dropped when closed.
    print('Lost client', websocket.uuid)
    if websocket.registered is True:
        drop_register(websocket.uuid)
    return await cluster.drop_socket(websocket)


async def onboard(websocket):
    """ Called by `capture` on first connection.
    """
    print('onboard Socket', websocket)
    websocket.count = 0
    websocket.uuid = -1
    websocket.registered = False


async def recv_message(websocket, message):
    """
    Receive the message from the given websocket - expecting JSON from the client.

    If the socket is new, expect a UUID message - it registers and calls
    cluster.new_socket. After the first call, all salls are sent to
    cluster.recv_message().
    """
    d = json.loads(message)
    if websocket.count == 0 or websocket.uuid == -1:
        print('Detected new socket')
        return await recv_new_socket(websocket, d)

    print('Recv', message)
    websocket.count += 1
    # send acceptance.
    await send_json(websocket, ok=True, code=1111, accept=len(message))
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
        print('Refuse client:', uuid)
        # https://github.com/Luka967/websocket-close-codes
        return await websocket.close(4001, reason='failed ID')
    # Store in the persistent.
    set_register(uuid, websocket)
    print('Recv', uuid)
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