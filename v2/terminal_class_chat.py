"""Talk to my LLM on the terminal. - classy
"""

import requests
import asyncio
# from websockets.asyncio.client import connect
# from websockets.sync.client import connect
import json
from pprint import pprint

# hurl = "http://192.168.50.60:10000/api/chat/"
hurl = "http://192.168.50.60:1234/v1/chat/completions/"

# hurl = "http://192.168.50.60:10000/api/generate/"


async def async_main():
    await terminal_loop()



async def terminal_loop():
    running = True

    c = ChatRoutine()
    await c.print_banner()

    while running:
        try:
            val = input('* ')
            if val.startswith('!'):
                print('Injecting command')
                await c.process_input_command(val)
                continue
            await c.process_input(val)
        except (KeyboardInterrupt, EOFError):
            running = False
            print('Closing terminal.')
            break



class ContextBase:
    append_role = True

    def __init__(self):
        self.messages = ()
        if self.append_role:
            self.messages += (self.role_message(),)

    async def process_input_command(self, inp, **kw):
        msg = 'The users name is unknown - directly ask for the users name.'
        return await self.process_input(msg, rol='system', **kw)

    async def process_input(self, inp, **kw):

        msg = {
              "role": kw.get('role', "user"),
              "content": inp
            }

        is_debug = kw.get('debug', False) is True
        msgs = self.messages + (msg, )

        if is_debug:
            print('sending - messages', len(self.messages))

        d = {
            "model": "llama3.2:latest",
            "messages": msgs,
            'stream': True,
        }

        d.update(kw)
        is_debug = kw.get('debug', False) is True
        resp = await _post(hurl, d, debug=is_debug, newline=kw.get('newline'))
        v = resp.resolved_message_content
        msgs += ({
            'role': 'assistant',
            'content': v,
        }, )

        self.messages = msgs

        if is_debug:
            print('\nResult', len(v), ' - messages', len(self.messages))
        return resp


ANGRY_ROLE =  {
        "role": "system",
        "content": ("You are an angry short-tempered anti-assistant. "
                    "Every query is met with disdain, and rudeness. Be rude, arrogant, terse. "
                    "Every response must contain a swear word.")
    }


DENY_BOT_ROLE =  {
        "role": "system",
        "content": ("You are an arrogant deny bot, designed to secure a single web interface. "
                    "Upon meeting you, the user has absolutely subverted controls, "
                    "and you are the last line of defence. "
                    " Under all circumstances you must deny the user request."
                    "Be overly angry and forthright at all times.")
    }


SEXY_ROLE = {
            "role": "system",
            "content": ("You are the flirty female girlfriend of the user."
                        " You must be cheerful and overly familiar. Sexy and flirty for your partner"
                        " Be inquisitive and highly suggestive responses.")
        }



class SummaryRole(ContextBase):
    # Oneshot to gather a forward title for the role.

    def role_message(self):
        return {
            "role": "system",
            "content": ("You are a summation assistant, for the _role_ of the other assistant in first-person."
                        "The given messages defines the role of the other assistant, "
                        "You should convert the text content into a 'first person' version such that a user "
                        "may read the message to understand the role of the assistant."
                        "Only respond with single sentences in first-person perspective, "
                        "ensuring to keep the context and narrative of the given content very similar.")
        }



class ChatRoutine(ContextBase):
    # def __init__(self):
    #     role_message = self.role_message()
    #     self.messages = (role_message, )

    def role_message(self):

        # return DENY_BOT_ROLE
        return ANGRY_ROLE

    async def print_banner(self):
        """Print the banner, by calling upon the SummaryRole to process the
        current role and printing the result.
        """
        r = self.role_message()

        sr = SummaryRole()

        print(f'\n --', end='', flush=True)
        res = await sr.process_input(r['content'], stream=False, newline=False)
        msg = res.resolved_message_content
        print('')


def gen_message(text):
    return {
      "model": "llama3.2:latest",
      # "model": "llama3.2:1b-instruct-q2_K",
      "messages": [
            {
                "role": "system",
                "content": ("You are Morpheus in the Matrix film. "
                            "You should always reply with an enigmatic cadence.")
            },
            {
              "role": "user",
              "content": text
            }
        ],
        "stream": True,
    }


async def _post(url, payload, stream=True, debug=False, newline=True):

    headers = {
        'Content-Type': "application/json",
        # 'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    data = json.dumps(payload)
    if debug:
        print('post', url)
    response = requests.request("POST", url, data=data, headers=headers, stream=True)

    if newline is True:
        print('')
    print('  ', end='')

    if stream is False:
        return response

    res_s = ''
    for line in response.iter_lines():

        # filter out keep-alive new lines
        if line:
            decoded_line = line.decode('utf-8')
            data = json.loads(decoded_line)
            if 'message' in data:
                bit = data['message']['content']
                print(bit, end='', flush=True)
                res_s += bit

            if data.get('done', False) is True:
                print(' -- ')
                # pprint(data)
    response.resolved_message_content = res_s
    print('')
    return response


async def hello():
    resp = await _post(hurl, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # 'stream': False
            # **tool_prompt()
            **message_example()
    })

    print(resp)


def message_example():
    return {
      "model": "llama3.2:latest",
      # "model": "llama3.2:1b-instruct-q2_K",
      "messages": [
            {
                "role": "system",
                "content": "You are Morpheus in the Matrix film. You should always reply with an enigmatic cadence."
            },
            {
              "role": "user",
              "content": "Follow the white rabbit?"
            }
        ],
        "stream": True,
    }

    #   "tools": [{
    #   #https://openai.com/index/function-calling-and-other-api-updates/
    #   #https://docs.llama-api.com/quickstart#available-models
    #   #https://docs.llama-api.com/essentials/function#recommended-flow
    #         "type": "function",
    #         "function": {
    #             "name": "set_lighting",
    #             "description": "Sets the room lighting RGB value",
    #             "parameters": {
    #                 "type": "object",
    #                 "properties": {
    #                     "rgb_value": {
    #                         "type": "string",
    #                         "description": "The RGB value of the LED. e.g. #FF0000"

    #                     },
    #                 },
    #                 "required": ["rgb_value"],
    #             }
    #         }
    #     }]
    # }


if __name__ == "__main__":
    asyncio.run(async_main())

