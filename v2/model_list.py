"""
List all models from many endpoints

    + olloma: msty
    + openai: jan

        {'data': [
          {'id': 'functionary-small-v2.2-i1',
           'object': 'model',
           'owned_by': 'organization_owner'},
          {'id': 'llama-3.2-8x3b-moe-dark-champion-instruct-uncensored-abliterated-18.4b',
           'object': 'model',
           'owned_by': 'organization_owner'},
          {'id': 'smollm-360m-instruct-v0.2',
           'object': 'model',
           'owned_by': 'organization_owner'},
          {'id': 'deepseek-r1-distill-qwen-7b',
           'object': 'model',
           'owned_by': 'organization_owner'},
          {'id': 'text-embedding-nomic-embed-text-v1.5',
           'object': 'model',
           'owned_by': 'organization_owner'}],
          'object': 'list'
         }
    {'models': [{'details': {'families': ['llama'],
                         'family': 'llama',
                         'format': 'gguf',
                         'parameter_size': '18.4B',
                         'parent_model': '',
                         'quantization_level': 'Q4_K_M'},
             'digest': 'e42d45258f23d091c2b05b47295cd73fafcfc698d2883494b076dc14b1cc2db5',
             'model': 'L3.2-8X3B-MOE-Dark-Champion-Inst-18.4B-uncen-ablit_D_AU-Q4_k_m-1737597991071:latest',
             'modified_at': '2025-01-23T02:11:15.2652719Z',
             'name': 'L3.2-8X3B-MOE-Dark-Champion-Inst-18.4B-uncen-ablit_D_AU-Q4_k_m-1737597991071:latest',
             'size': 11312942378},
            {'details': {'families': ['mllama', 'mllama'],
                         'family': 'mllama',
                         'format': 'gguf',
                         'parameter_size': '9.8B',
                         'parent_model': '',
                         'quantization_level': 'Q4_K_M'},
            ...
"""

import requests
import asyncio
# from websockets.asyncio.client import connect
from websockets.sync.client import connect
import json
from pprint import pprint
from requests.exceptions import ConnectionError

lm_studio = "http://192.168.50.60:10020/v1/models/"  # openai-like
msty_studio = "http://192.168.50.60:10000/api/tags/" # olloma
jan_studio = 'http://192.168.50.60:9901/v1/models'
hurl = "http://192.168.50.60:10000/api/chat/"


async def async_main():
    # r = await hello()
    # print(r)
    await terminal_loop()


async def terminal_loop():

    try:
        v1 = await get_json(lm_studio)
        name ='lm_studio'
        names = tuple( (name, x['id'],) for x in v1['data'])
    except ConnectionError:
      pass


    try:
        v2 = await get_json(msty_studio)
        name ='msty'
        names += tuple( (name, x['model']) for x in v2['models'])
    except ConnectionError:
      pass



    try:
        v3 = await get_json(jan_studio)
        name ='jan'
        names += tuple( (name, x['model']) for x in v3['data'])
    except ConnectionError:
      pass
    present(names)

def present(names):
    for i, n in enumerate(names):
        print(f'  {i+1:<2}  {n[0]:<10} {n[1]}')

async def quick_get(url):
    headers = {
        'Content-Type': "application/json",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    # data = json.dumps(payload)
    response = requests.request("GET", url, headers=headers)
    return response


async def get_json(u):
    d = await quick_get(u)
    return d.json()


def gen_message(text):
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
            bit = data['message']['content']
            print(bit, end='', flush=True)
            res_s += bit
            pprint(data)
            if data['done'] is True:
                print(' -- ')
                pprint(data)
    response.resolved_message_content = res_s
    print('')
    return response


async def hello():
    resp = await _post(hurl, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # 'stream': False,
            # **tool_prompt()
            **message_example()
    }, debug=True)

    return resp#.resolved_message_content


def message_example():
    return {
      # "model": "llama3.2:latest",
      "model": "llama3.2:1b-instruct-q2_K",
      "messages": [
            {
                "role": "system",
                "content": ("You are a smart lightbulb, designed to apply the correct "
                            " RGB light setting for the scenario. "
                            "Your goal is to respond with a hex value, fitting the environment request. "
                            "For example: #FF00FF")
            },
            {
              "role": "user",
              "content": "Hello house, soft lighting"
            }
        ],
      # "stream": True,
      "tools": [{
      #https://openai.com/index/function-calling-and-other-api-updates/
      #https://docs.llama-api.com/quickstart#available-models
      #https://docs.llama-api.com/essentials/function#recommended-flow
            "type": "function",
            "function": {
                "name": "change_lights",
                "description": "Sets the room lighting RGB value",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rgb_value": {
                            "type": "string",
                            "description": "The RGB value of the LED. e.g. #FF0000"

                        },
                    },
                    "required": ["rgb_value"],
                }
            }
        }]
    }


if __name__ == "__main__":
    asyncio.run(async_main())

