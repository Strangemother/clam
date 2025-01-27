"""The cluster handles all incoming transactions
A client has an id for the session (for now)

Messages inbound from the websocket are expected JSON.
Farm results through the cluster as needed.
"""

from collections import defaultdict
from head import Alpha

mems = {}

def get_mem(uuid, websocket):
    if uuid in mems:
        return mems[uuid]
    mems[uuid] = Alpha(uuid)
    return mems[uuid]


async def recv_message(websocket, data):
    uuid = websocket.uuid
    print('cluster', data, 'from', uuid)
    head = get_mem(uuid, websocket)
    await head.recv_message(websocket, data)


async def new_socket(websocket, data):
    uuid = websocket.uuid
    print('new socket', 'uuid', uuid)
    head = get_mem(uuid, websocket)
    await head.wake(websocket, data)
    # head.open_time =
