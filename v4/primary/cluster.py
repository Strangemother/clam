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
from datetime import datetime
from uuid import uuid4
import json
import asyncio
from loguru import logger


log = logger.debug


# Map the UUID to the associated socket.
uuid_ws_map = {}

# Map the UUID to the associated wrapper.
uuid_wrapper_map = {}

# Map the given role to many UUID's
# Created on entry for a new socket.
role_uuid_map = defaultdict(list)


#"role" mapping of clients.
CLUSTER_CONFIG = {
    # Messages from the user primary (the UI), to the _alpha_ outputs.
    "user::primary": ["memory"],
    # All alpha messages return to the user.
    "memory": ["memory::layer2"],
    "memory::layer2": ["user::primary"],
}


def str_uuid4():
    return str(uuid4())


async def new_socket(websocket, data):
    """The new socket has appeared; this first entrance (after the accepted, and
    first messaging clauses), captures and onboards the socket into the cluster.

    The socket is bi-directional, so we can ask it questions, such as 'abilities.'

    However in first draft this can be given in the first message here (`data`)

    ---

    The `get_mem` will return the internal class wrapper for the socket.
    The `head` maintains state and internal changes.
    """
    uuid = websocket.uuid
    log(f'cluster.new_socket {uuid=}, setting memory with {data=}')
    head = set_mem(uuid, websocket, data)

    ## is SocketWrapper
    session_id:SocketWrapper = await head.wake(websocket, data)
    # head.open_time =

    ## We need a session ID. Something that doesn't change throughout a conversation.
    ## This should be associated with the user, for history continuation.
    ## for now, this can be a new one for the connected socket.
    ## A change can be requested by the user later.


def get_mem(uuid, websocket, **data):
    """Get or create the socket store, bound by its UUID (already assigned by
    the incoming socket manager).

    Notably this memory unit thing, is not websocket bound. As a socket can
    change, but the memory unit remains
    """
    if uuid in uuid_wrapper_map:
        return uuid_wrapper_map[uuid]
    return set_mem(uuid, websocket, data)



def set_mem(uuid, websocket, data):
    """The `get_mem` is _get or create_, but to ensure we store the
    bound values correctly, an explicit `set_mem` is called upon a new socket.

    The data contains the important knowledge of a connecting client.

        head = set_mem(uuid, websocket, data)
    """
    uuid_wrapper_map[uuid] = wrap_socket(uuid, websocket, data)
    uuid_ws_map[uuid] = websocket
    role = data.get('role')
    log(f'Storing {role=} as {uuid=}')
    role_uuid_map[role] += [uuid,]
    return uuid_wrapper_map[uuid]


async def drop_socket(websocket):
    """Called by the primary capture loop, when a registered socket
    is dropped. As the socket is lost, remove it from the graph.
    """
    uuid = websocket.uuid
    if uuid == -1:
        # never assigned.
        return uuid

    wrapper = uuid_wrapper_map[uuid]
    role = wrapper.role
    del uuid_wrapper_map[uuid]
    del uuid_ws_map[uuid]

    if uuid in role_uuid_map[role]:

        # i = role_uuid_map[role].index(uuid)
        role_uuid_map[role].remove(uuid)
    else:
        log(f'{uuid=} was not in {role=} stack {role_uuid_map=}')
    return uuid


def role_to_uuids(role):
    """Given a role, return UUIDs currently associated
    with that role.
    """
    return role_uuid_map.get(role, None) or []


def uuid_to_wrapper(uuid):
    """Given a UUID return the associated socket.
    This is an informed function - will break when called without a valid
    uuid.
    """
    return uuid_wrapper_map[uuid]


def uuid_to_socket(uuid):
    return uuid_ws_map[uuid]


def wrap_socket(uuid, socket, data):
    """Return an object to associate this ID with this socket.
    The ID is bound to the graph, the socket is bound to the ID, but can
    transition away.
    """
    return SocketWrapper(uuid, data)


class SocketWrapper:
    role = None

    def __init__(self, uuid, config=None):
        log(f'New "{self.__class__.__name__}" session {uuid=}')
        self.uuid = uuid
        self.open_time = datetime.now()
        self.recv_count = 0

        # init data given by the wakeup (set_mem -> wrap_socket)
        # it should contain (at the least) a "role".
        self.config = config or {}
        self.role = self.config.get('role')

        self.stream_mode = False
        self.stream_meta = None

    async def wake(self, websocket, data):
        """First call from the websocket.

        + Create a unique session id; this may change later (upon user request)

        """
        self.session_id = data.get('session_id', str_uuid4())

        return await self.send_json(
            websocket,
            session_id=self.session_id,
            text='Hello.',
            code=1200
            )

    async def send_text(self, websocket, text):
        return await self.send_json(websocket, text=text)

    async def send_json(self, websocket, **kw):
        # log(f"wrapper {self.uuid=} sending json to {websocket.uuid=}, {kw=}")
        return await websocket.send(json.dumps(kw))

    async def recv_message(self, websocket, data):
        """A message from the client socket received through the general loop
        callback.

        the websocket.uuid should match self.uuid, but this doesn't matter.
        The session should exist to communicate to the bot.
        """
        self.recv_count += 1
        # log(f'Message {self.uuid=} {websocket.uuid=}')
        # data['origin_ids'] = [self.uuid, websocket.uuid]
        code = data.get('code')
        if code == 1515:
            log('open stream')
            return await self.start_recv_message_stream(websocket, data)

        if code == 1516:
            log('close stream')
            return await self.stop_recv_message_stream(websocket, data)

        if self.stream_mode:
            await asyncio.sleep(.01)
            return await self.from_stream_message(websocket, data)
        return await self.from_message(websocket, data)

    async def from_stream_message(self, websocket, data):
        data.update(self.stream_meta)
        return data

    async def from_message(self, websocket, data):

        # Origin ID doesn't change is kept throughout the chain.
        # Given before this receiver.
        # data['origin_id'] = str_uuid4()

        # The session ID doesn't change throughout the connection mostly.
        session_id = data.get('session_id', self.session_id)
        data['session_id'] = session_id

        # The current (new) message id.
        data['message_id'] = str_uuid4()
        return data

    async def start_recv_message_stream(self, websocket, data):
        """Code 1515 denotes open stream. data is propped
        """
        self.stream_mode = True
        self.stream_meta = data['meta']
        websocket.receipts = False
        return data

    async def stop_recv_message_stream(self, websocket, data):
        """Code 1516 denotes close stream. data is propped
        """
        self.stream_mode = False
        self.stream_meta = None
        websocket.receipts = True
        return data


async def recv_message(websocket, data):
    """First function called by the primary.run::recv_message
    providing the websocket and its buffered message.
    """
    uuid = websocket.uuid
    # log(f"cluster {data=} from {uuid=}")
    head = get_mem(uuid, websocket)

    # the socket wrapper cleans the message. Converts, or waits.
    cd = await head.recv_message(websocket, data)

    """Here - the head must assess and farm the message.
    In most cases the message doesn't change - the memory, thinkers etc...
    all have the same info.
    """
    return await dispatch_through_graph(head, websocket, cd)


async def dispatch_through_graph(head, websocket, data):
    """Called by the recv_message providing the `head` internal class instance
    (e.g. `SocketWrapper`), the calling `websocket`, and its `data` message.

    Send this message to the designated clients.
    """
    # Cluster sends to configured destination.
    role = head.role
    destinations = CLUSTER_CONFIG[role]

    # log(f'{role=} message => dispatch_through_graph to {destinations=}')
    for dest_role in destinations:
        # role to uuid maps.
        uuids = role_to_uuids(dest_role)

        # log(f'{dest_role=} to {uuids=}')

        for dest_uuid in uuids:
            dest_head = uuid_to_wrapper(dest_uuid)
            # log(f"Message heading to {dest_head=}")
            dest_websocket = uuid_to_socket(dest_uuid)
            # log(f'_- Destination socket: {dest_websocket.uuid=}')
            await dest_head.send_json(dest_websocket, **data)
            # log(f'^- Destination socket done: {dest_websocket.uuid=}')

        # log(f'  Done {dest_role=}')
    # log('... All dispatch_through_graph complete.')

