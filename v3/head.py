"""The cluster handles all incoming transactions
A client has an id for the session (for now)

Messages inbound from the websocket are expected JSON.
Farm results through the cluster as needed.
"""
import requests
import json

ANGRY_ROLE =  {
    "role": "system",
    "content": ("You are an angry short-tempered anti-assistant. "
                "Every query is met with disdain, and rudeness. Be rude, arrogant, terse. "
                "Every response must contain a swear word.")
}

configs = {
    "default": {
        'foreground': {
            'url': "http://192.168.50.60:10000/api/chat/",
            'model': "llama3.2:latest"
        }
    }
}

from clients import get_register
from shorts import send_json


async def send_service_text(websocket, t):
    return await send_json(websocket, text=t)


class OllomaClient:
    append_role = True
    url = "http://192.168.50.60:10000/api/chat/"
    model = "llama3.2:latest"

    def __init__(self, head, write_back=None, **kw):
        self.head = head
        self.write_back = write_back or self.print_bit
        self.messages = ()
        self.__dict__.update(**kw)

        if self.append_role:
            self.messages += (self.role_message(),)

    def role_message(self):
        return ANGRY_ROLE

    async def wake(self, data):
        print('Wake OllomaClient')

    def is_streaming(self):
        return False

    async def process_input(self, content):
        msg = dict(
            role='user',
            content=content,
        )
        msgs = self.messages + (msg, )

        d = {
            "model": self.model,
            "messages": msgs,
            'stream': True,
        }

        return await self.post(self.url, d)

    async def post(self, url, d):
        headers = {
                'Content-Type': "application/json",
                'Cache-Control': "no-cache",
            }

        data = json.dumps(d)
        print('POST', url)
        response = requests.request("POST", url, data=data,
                                    headers=headers, stream=True)


        for line in response.iter_lines():

            # filter out keep-alive new lines
            if not line:
                continue

            decoded_line = line.decode('utf-8')
            data = json.loads(decoded_line)
            await self.write_back(data)
            # self.print_bit(data)

    def print_bit(self, data):
        bit = data['message']['content']
        print(bit, end='', flush=True)

        if data['done'] is True:
            print(' -- ')


class Alpha:

    def __init__(self, uuid):
        print('New session', uuid)
        self.uuid = uuid

    async def wake(self, websocket, data):
        """Very First call on new socket.
        This should prepend all services and wake the consortium
        """
        config_name = data.get('config', 'default')
        self.config = configs.get(config_name)
        print('Wake services with ', data)
        await send_service_text(websocket, 'waking clients')
        self.foreground = OllomaClient(head=self, write_back=self.foreground_recv)
        await self.foreground.wake(data)
        self.foreground_uuid = websocket.uuid

    async def recv_message(self, websocket, data):
        """A message from the client socket into the head.

        the websocket.uuid should match self.uuid, but this doesn't matter.
        The session should exist to communicate to the bot.
        """

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
            pass

        content = data['text'] #from client socket.
        await fgc.process_input(content)

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
    async def foreground_recv(self, data):
        print('Said', data)
        # send a foreground partial to the UI.

        # push to UI.
        ws = get_register(self.foreground_uuid)
        return await send_json(ws,
            node='foreground',
            n='fg',
            type="partial",
            t="p",
            done=data["done"],
            d=int(data["done"]),
            **data['message'],
            )
