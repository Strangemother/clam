"""The cluster handles all incoming transactions
A client has an id for the session (for now)

Messages inbound from the websocket are expected JSON.
Farm results through the cluster as needed.
"""
import requests
import asyncio
import json

from http_tools import http_quick_get, http_post_json, http_get_json
from atimer import Timer
from clients import get_register, OllomaClient
from shorts import send_json

from datetime import datetime

import asyncio


ANGRY_ROLE =  {
    "role": "system",
    "content": ("You are an angry short-tempered anti-assistant. "
                "Every query is met with disdain, and rudeness. Be rude, arrogant, terse. "
                "Every response must contain a swear word.")
}


LAYER1_ROLE =  {
    "role": "system",
    "content": ('You are the first assistant of a knowledge cluster for user inputs.\n '
                'Deeply consider the users input, evaluating the idea in all '
                'aspects. Detail related thoughts, concepts, or information '
                'in the conversation, to apply associated knowledge to the '
                'recent message for the purposes of further discussion.')
}


layer_1_kw = {
    'role': LAYER1_ROLE,
    'model': "gemma2:2b",
    # 'model': "deepseek-r1:latest",
}

foreground_kw = {
    "role":ANGRY_ROLE,
    'model': "gemma2:2b",
    # 'model': "llama3.2:latest",
}

configs = {
    "default": {
        'foreground': {
            'url': "http://192.168.50.60:10000/api/chat/",
            'model': "llama3.2:latest"
        }
    }
}


async def send_service_text(websocket, t):
    return await send_json(websocket, text=t)

from collections import defaultdict

class Alpha:

    def __init__(self, uuid):
        print(f'New "{self.__class__.__name__}" session', uuid)
        self.recv_count = 0
        self.last_recv_count = 0
        self.uuid = uuid
        self.open_time = datetime.now()
        self.recv_timer = Timer(10, self.recv_timeout_callback)
        print('Timer', self.recv_timer)
        self.foreground_stream_data = ''
        self.live_streams = defaultdict(str)

    async def recv_timeout_callback(self):
        # push a message into the foreground conversation, as the system.
        self.recv_timer = None
        if self.recv_count > self.last_recv_count:
            return

        await asyncio.sleep(0.1)

        print('background question!')
        fgc = self.foreground
        last_message = 'is blank (user has not entered any text)'
        fgc = self.foreground
        lm = fgc.last_message()
        if lm:
            if lm['role'] not in ('assistant', 'system',):
                last_message = lm['content']

        msg = ('[CONTEXT] The user has said nothing since: "'
                f"{last_message}"
                '". Prompt them to provide input whilst ensuring '
                'to reference to the the message in first-person perspective. [/CONTEXT]')
        # msg = (
        #         '[CONTEXT]'
        #         'role: system \n This is the background system. '
        #         # 'A background alert occured: `doorbell`. '
        #         # 'your memory about "welsh presenter" is saved.'
        #         'Directly but tersely announce this event to the user in first person perspective. '
        #         '[/CONTEXT]'
        #         )
        print('Posting', msg)

        # await fgc.process_input("The users name is Jay", 'system')
        await fgc.process_input(msg)

    async def wake(self, websocket, data):
        """Very First call on new socket.
        This should prepend all services and wake the consortium
        """
        config_name = data.get('config', 'default')
        self.config = configs.get(config_name)
        # print('Wake services with ', data)
        await send_service_text(websocket, 'waking clients')
        self.foreground = OllomaClient(head=self, write_back=self.foreground_recv, **foreground_kw)
        self.layer_1 = OllomaClient(head=self, write_back=self.layer_1_recv, **layer_1_kw)
        self.foreground_uuid = websocket.uuid
        await self.wake_client(self.layer_1, websocket, data)
        return await self.wake_client(self.foreground, websocket, data)

    async def wake_client(self, client, websocket, data):
        result = await self.foreground.wake(data)

        if result is not None:
            # print('Resulting wake result', result)
            # This result is sent back to the client.
            model_data = await send_json(websocket, **result)
            return model_data

    async def recv_message(self, websocket, data):
        """A message from the client socket into the head.

        the websocket.uuid should match self.uuid, but this doesn't matter.
        The session should exist to communicate to the bot.
        """
        self.recv_count += 1
        print('Message', self.uuid, websocket.uuid)
        """Here - the head must assess and farm the message.
        In most cases the message doesn't change - the memory, thinkers etc...
        all have the same info.

        They message back to this head, flourishing the foreground.

        we need
            foreground
            primary
            thinker
            memory

        For now - A simple chat bot without the primary - extended later.
        """
        fgc = self.foreground
        if fgc.is_streaming:
            # interrupt?
            print('!IS STREAMING!')
            pass

        role = data.get('role', 'user')
        if role in ('user', ):
            return await self.recv_message_user(websocket, data)

        print('sys message - ', role)
        # service, system, user
        mname = f"recv_message_{role}"
        return await getattr(self, mname)(websocket, data)
        # the primary (here) can be responsible for content interruptions.
        # This cell is bound to the socket; So the bot is continuing to chat.
        # We can shoot messages to _stop_ , or _other thoughts_, of which
        # the primary can challenge concurrent actions...
        #
        #
        # Therefore if the "foreground" or thinker is busy, we can test and
        # do other things:
        # if self.foreground.is_streaming:
        #   message = self.infer_concurrent_action()
        #   if message.is_halting:
        #    ... stop.
        #
        """
        What is the captial of france
            ....
        stop talking
            [current context is stopped; and a new one is generated with this partial applied...]
        """

    async def recv_message_system(self, websocket, data):
        """Receive a message of a 'user' role. This is processed as conversation.
        """
        print('Process system message')
        fgc = self.foreground
        content = data['text'] #from client socket
        role = data.get('role', 'system') # as a 'system'
        await fgc.process_input(content, role)

        if self.recv_timer is None:
            self.last_recv_count = self.recv_count
            self.recv_timer = Timer(1, self.recv_timeout_callback)

    async def recv_message_user(self, websocket, data):
        """Receive a message of a 'user' role.
        This is processed as conversation and sent to the foreground, and the
        layer_1 (layer 1.)
        """
        fgc = self.foreground
        l1c = self.layer_1

        content = data['text'] #from client socket.
        await fgc.process_input(content)
        await l1c.process_input(content)

        if self.recv_timer is None:
            self.last_recv_count = self.recv_count
            self.recv_timer = Timer(4, self.recv_timeout_callback)

    async def recv_message_service(self, websocket, data):
        """A Service message is not directly conversation bound, such as model
        changes or background events.
        """
        print('Background event.', data)
        action = data.get('action')
        mname = f"recv_message_service_action_{action}"
        return await getattr(self, mname)(websocket, data)

    async def recv_message_service_action_select_models(self, websocket, data):
        """
            {'role': 'service', 'action': 'select_models', 'models': ['deepseek-r1:latest']}

            In the future this will select a layer in the cluster.
        """
        models = data.get('models', ())
        fgc = await self.foreground.set_model(models[0])
        # if wake - post an empty message.

    async def layer_1_recv(self, data):
        """The first layer responds with a deeper thought on the given input.
        """
        print(',', end='')
        client = self.layer_1
        node = 'layer_1'
        ## We still send the layer 1 node into to the foreground socket bitstream.
        socket_uuid = self.foreground_uuid
        return await self.outbound_bitstream(data, client, node, socket_uuid)

    async def foreground_recv(self, data):
        """This method is hooked to the olloma client, receiving messages
        from the bot in real-time.

        Once the message is `done=True`, the response is sent to the other
        machinery.

            {
                'model': 'llama3.2:latest',
                'created_at': '2025-01-29T01:33:44.1530517Z',
                'message': {'role': 'assistant', 'content': ''},
                'done_reason': 'stop',
                'done': True,
                'total_duration': 484904800,
                'load_duration': 15315700,
                'prompt_eval_count': 31,
                'prompt_eval_duration': 1000000,
                'eval_count': 11,
                'eval_duration': 467000000
            }
        """
        print('.', end='')
        client = self.foreground
        socket_uuid = self.foreground_uuid
        node = 'foreground'
        return await self.outbound_bitstream(data, client, node, socket_uuid)

    async def outbound_bitstream(self, data, client, node, socket_uuid):
        # send a foreground partial to the UI.

        live_in = self.live_streams[node]
        # push to UI.
        done = data.get("done", -1)
        if done is True:
            # Stash message
            d = {
                'content': live_in,
                'role': data['message']['role'],
            }
            client.messages += (d, )
            self.live_streams[node] = ''

        else:
            try:
                bit = data['message']['content']
                self.live_streams[node] += bit
            except KeyError:
                print('Error with data', data)

        await asyncio.sleep(0)
        model = data.get('model', None)
        wm = f'service unpackaged an empty message object from the live stream {node}'
        kw = dict(
            # n='fg',
            # t="p",
            # d=int(done),
            node=node,
            type="partial",
            done=done,
            **data.get('message', { 'warning': wm}),
            model=model,
        )

        for k in data:
            if k in kw:
                continue
            kw[k] = data[k]

        ws = get_register(socket_uuid)
        await send_json(ws,**kw)
