"""Talk to my LLM on the terminal.
"""

import requests
import asyncio
# from websockets.asyncio.client import connect
from websockets.sync.client import connect
import json
from pprint import pprint

hurl = "http://192.168.50.60:10000/api/chat/"
# hurl = "http://192.168.50.60:10000/api/generate/"


async def _post(url, payload):

    headers = {
        'Content-Type': "application/json",
        # 'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    data = json.dumps(payload)
    print('post', url)
    response = requests.request("POST", url, data=data, headers=headers, stream=True)

    print('')
    print('  ', end='')
    for line in response.iter_lines():

        # filter out keep-alive new lines
        if line:
            decoded_line = line.decode('utf-8')
            # pprint(json.loads(decoded_line))
            print(json.loads(decoded_line)['message']['content'], end='')

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
    asyncio.run(hello())

