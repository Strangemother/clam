"""
Functions to communicate to a remote LLM.
This is the no-stream content.
"""

import requests
import asyncio
# from websockets.asyncio.client import connect
# from websockets.sync.client import connect
import json
from pprint import pprint

#lm studio
hurl = "http://192.168.50.60:1234/v1/chat/completions/"
# hurl = "http://192.168.50.60:10000/api/generate/"
chat_url = "http://192.168.50.60:1234/api/chat/"


async def async_post(url, payload):

    headers = {
        'Content-Type': "application/json",
        # 'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    data = json.dumps(payload)
    print('post', url)
    for msg in payload['messages']:
        print('  >  ', f"{msg['role']:<12} {msg['content']}")
    response = requests.request("POST", url, data=data, headers=headers, stream=True)
    # print('\nResponse:')
    data = response.json()
    print('  <   ', end='')
    msg = data['choices'][0]['message']
    print(f"{msg['role']:<12} {msg['content']}")
    return "\n.Done"
    # print(data['choices'][0]['message'])
    # print(data['choices'][0]['message']['content'])


def print_payload_messages(payload):
    for msg in payload['messages']:
        print('  >  ', f"{msg['role']:<12} {msg['content']}")


def print_content_response(json_data):
    # json_data = response.json()
    print('  <   ', end='')
    msg = json_data['choices'][0]['message']
    print(f"{msg['role']:<12} {msg['content']}")


def plain_post(url, payload):

    headers = {
        'Content-Type': "application/json",
        # 'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    data = json.dumps(payload)
    print('post', url)
    response = requests.request("POST", url, data=data, headers=headers, stream=True)
    # print('\nResponse:')
    data = response.json()
    # msg = data['choices'][0]['message']
    # print(f"{msg['role']:<12} {msg['content']}")
    return data
    # print(data['choices'][0]['message'])
    # print(data['choices'][0]['message']['content'])


def send_wait(content=None, role=None, model=None):
    resp = plain_post(hurl, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # **tool_prompt()
            **make_message(content, role, model)
    })
    # print('send_wait complete')
    return resp


def send_conversation(data):
    resp = plain_post(hurl, data)
    # print('send_wait complete')
    return resp


def send_wait_message(message):
    resp = plain_post(hurl, message)
    # print('send_wait complete')
    return resp



async def hello():
    resp = await async_post(hurl, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # **tool_prompt()
            **make_message()
    })

    print(resp)


def make_message(content=None, role=None, model=None):

    content = content or  "What is your favourite fruit? Please answer in one word"
    role = role or  "user"
    model = model or  "granite-4.0-h-tiny"

    return {
      # "model": "llama3.2:latest",
      "model": model,
      "messages": [
            # {
            #     "role": "system",
            #     "content": "You are a one word answer bot. answer with one Word. 'banana'"
            #     # "content": "You are Morpheus in the Matrix film. You should always reply with an enigmatic cadence."
            # },
            {
              "role": role,
              # "content": "Follow the white rabbit?"
              "content": content
            }
        ],
        "stream": False,
        "metadata": { 'topic': 'excel'}
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
    asyncio.run(hello())

