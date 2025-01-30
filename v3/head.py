"""The cluster handles all incoming transactions
A client has an id for the session (for now)

Messages inbound from the websocket are expected JSON.
Farm results through the cluster as needed.
"""
import requests
import asyncio
import json

from clients import get_register
from shorts import send_json

from datetime import datetime

import asyncio


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

async def send_service_text(websocket, t):
    return await send_json(websocket, text=t)

async def http_quick_get(url):
    headers = {
        'Content-Type': "application/json",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    print(' -- http_quick_get', url)
    # data = json.dumps(payload)
    response = requests.request("GET", url, headers=headers)
    return response

async def http_post_json(url, d, reader=None):
    headers = {
            'Content-Type': "application/json",
            'Cache-Control': "no-cache",
        }

    data = json.dumps(d)
    print('JSON POST', url)
    stream = True
    response = requests.request("POST", url, data=data,
                                headers=headers, stream=stream)
    rows = ()
    for line in response.iter_lines():
        # filter out keep-alive new lines
        if not line:
            continue
        decoded_line = line.decode('utf-8')
        rl = json.loads(decoded_line)
        if reader:
            reader(rl, response)
        rows += (rl,)
    return rows


async def http_get_json(u):
    d = await http_quick_get(u)
    return d.json()



class OllomaClient:
    append_role = True
    url = "http://192.168.50.60:10000/api/chat/"
    model = "llama3.2:latest"
    # model = "deepseek-r1:latest"
    # model = "L3.2-8X3B-MOE-Dark-Champion-Inst-18.4B-uncen-ablit_D_AU-Q4_k_m-1737597991071:latest"
    def __init__(self, head, write_back=None, **kw):
        self.head = head
        self.write_back = write_back or self.print_bit
        self.messages = ()
        self.__dict__.update(**kw)
        self._is_streaming = False

        if self.append_role:
            self.messages += (self.role_message(),)

    async def set_model(self, model_name):
        # If an empty prompt is provided, the model will be loaded into memory.

        # Request
        # curl http://localhost:11434/api/generate -d '{
        #   "model": "llama3.2"
        # }'
        self.model = model_name
        url = "http://192.168.50.60:10000/api/generate/"
        r = await http_post_json(url, {'model': model_name})
        print('set model response', r)

    def last_message(self):
        return self.messages[-1]

    def role_message(self):
        return ANGRY_ROLE

    async def wake(self, data):
        print('Wake OllomaClient')
        # push models
        url = "http://192.168.50.60:10000/api/tags/"
        models = await http_get_json(url)
        models['type'] = 'models'
        return models

    def is_streaming(self):
        return self._is_streaming

    async def process_input(self, content, role='user'):
        msg = dict(
            role=role,
            content=content,
        )
        print('In', msg)
        msgs = self.messages + (msg, )

        d = {
            "model": self.model,
            "messages": msgs,
            'stream': True,
        }

        self.messages = msgs
        return await self.post(self.url, d)

    async def post(self, url, d):
        headers = {
                'Content-Type': "application/json",
                'Cache-Control': "no-cache",
            }

        data = json.dumps(d)
        print('POST', url)
        stream = True
        response = requests.request("POST", url, data=data,
                                    headers=headers, stream=stream)
        self._is_streaming = stream
        for line in response.iter_lines():
            # filter out keep-alive new lines
            if not line:
                continue
            decoded_line = line.decode('utf-8')
            data = json.loads(decoded_line)
            await self.write_back(data)
            # self.print_bit(data)
        self._is_streaming = False

    def print_bit(self, data):
        bit = data['message']['content']
        print(bit, end='', flush=True)

        if data['done'] is True:
            print(' -- ')



class Timer:
    """
    async def timeout_callback():
        await asyncio.sleep(0.1)
        print('echo!')

    print('\nfirst example:')
    timer = Timer(2, timeout_callback)  # set timer for two seconds
    await asyncio.sleep(2.5)  # wait to see timer works

    print('\nsecond example:')
    timer = Timer(2, timeout_callback)  # set timer for two seconds
    await asyncio.sleep(1)
    timer.cancel()  # cancel it
    """
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()


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

    async def recv_timeout_callback(self):
        # push a message into the foreground conversation, as the system.
        self.recv_timer = None
        if self.recv_count > self.last_recv_count:
            return

        await asyncio.sleep(0.1)
        print('background question!')
        fgc = self.foreground
        last_message = '[NEVER PROVIDED]'
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
        self.foreground = OllomaClient(head=self, write_back=self.foreground_recv)
        result = await self.foreground.wake(data)
        self.foreground_uuid = websocket.uuid

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
        """Receive a message of a 'user' role. This is processed as conversation.
        """
        fgc = self.foreground
        content = data['text'] #from client socket.
        await fgc.process_input(content)

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

    async def foreground_recv(self, data):
        """
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
        # send a foreground partial to the UI.

        live_in = self.foreground_stream_data
        # push to UI.
        done = data.get("done", -1)
        if done is True:
            # Stash message
            d = {
                'content': live_in,
                'role': data['message']['role'],
            }
            self.foreground.messages += (d, )
            self.foreground_stream_data = ''
        else:
            try:
                bit = data['message']['content']
                self.foreground_stream_data += bit
            except KeyError:
                print('Error with data', data)

        await asyncio.sleep(0)

        kw = dict(
            node='foreground',
            n='fg',
            type="partial",
            t="p",
            done=done,
            d=int(done),
            **data['message'],
            model=data['model'],
        )

        for k in data:
            if k in kw:
                continue
            kw[k] = data[k]

        ws = get_register(self.foreground_uuid)
        await send_json(ws,**kw)
