"""Talk to my LLM on the terminal.
"""

import requests
import asyncio
# from websockets.asyncio.client import connect
# from websockets.sync.client import connect
import json
from pprint import pprint

hurl = "http://192.168.50.60:1234/v1/chat/completions/"
# hurl = "http://192.168.50.60:10000/api/generate/"


async def _post(url, payload):

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


async def hello():
    resp = await _post(hurl, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # **tool_prompt()
            **message_example()
    })

    print(resp)


def message_example():
    return {
      # "model": "llama3.2:latest",
      "model": "granite-4.0-h-350m-unsloth-hybrid",
      "messages": [
            # {
            #     "role": "system",
            #     "content": "You are a one word answer bot. answer with one Word. 'banana'"
            #     # "content": "You are Morpheus in the Matrix film. You should always reply with an enigmatic cadence."
            # },
            {
              "role": "user",
              # "content": "Follow the white rabbit?"
              "content": "What is your favourite fruit? Please answer in one word"

            }
        ],
        "stream": False,
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

