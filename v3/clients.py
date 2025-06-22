from http_tools import http_quick_get, http_post_json, http_get_json
import json
import requests

REGISTER = {

}


def set_register(uuid, websocket):
    REGISTER[uuid] = websocket


def drop_register(uuid):
    del REGISTER[uuid]


def get_register(uuid):
    return REGISTER[uuid]


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
        self._role_message = kw.get('role')

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
        return self._role_message

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
        msgs = self.messages + (msg, )

        print('Sending', len(msgs), f' as {role=} messages to', self.model)

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

