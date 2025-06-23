"""# Cluster

> The cluster handles all incoming transactions from the websocket machine

The `run.py` calls the cluster with a ready websocket client (it's ID'd and
registered - waiting on messages)

+ A client has an id for the session (for now)
+ Messages inbound from the websocket are expected JSON.
+ Farm results through the cluster as needed.


On a new socket:

    async def recv_new_socket(websocket, message:str):
        # Called on first stream in. message is the _first_ message, expected
        # to be some authy (e.g the session login id)
        data = json.loads(message)
        return await cluster.new_socket(websocket, data)

On every message after:

    async def recv_message(websocket, message):
    d = json.loads(message)
    await cluster.recv_message(websocket, d)


Notably `run::recv_message` does this automatically.

---

The "Cluster" is a postman style delivery of messages across connected users.

A Message may be from the _user_ to other connected clients (abilities)


"""

from collections import defaultdict

mems = {}

def get_mem(uuid, websocket):
    if uuid in mems:
        return mems[uuid]
    mems[uuid] = uuid
    return mems[uuid]


async def recv_message(websocket, data):
    uuid = websocket.uuid
    print('cluster', data, 'from', uuid)
    head = get_mem(uuid, websocket)
    ## if head is obj.
    # await head.recv_message(websocket, data)


async def new_socket(websocket, data):
    uuid = websocket.uuid
    print('new socket', 'uuid', uuid)
    head = get_mem(uuid, websocket)

    ## If the response is a obj
    # await head.wake(websocket, data)
    # head.open_time =
