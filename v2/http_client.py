import requests
import asyncio
# from websockets.asyncio.client import connect
from websockets.sync.client import connect
import json

hurl = "http://192.168.50.60:10000/api/generate/"


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
            print(json.loads(decoded_line)['response'], end='')

    print('')
    return response

async def hello():
    resp = await _post(hurl, {
            'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # 'stream': False
            **tool_prompt()
    })

    print(resp)


def tool_prompt():
    return {
      # "model": "llama3.2",
      "messages": [
        {
          "role": "user",
          "content": "What is the weather today in Paris?"
        }
      ],
      "stream": True,
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "get_current_weather",
            "description": "Get the current weather for a location",
            "parameters": {
              "type": "object",
              "properties": {
                "location": {
                  "type": "string",
                  "description": "The location to get the weather for, e.g. San Francisco, CA"
                },
                "format": {
                  "type": "string",
                  "description": "The format to return the weather in, e.g. 'celsius' or 'fahrenheit'",
                  "enum": ["celsius", "fahrenheit"]
                }
              },
              "required": ["location", "format"]
            }
          }
        }
      ]
    }


async def hello_client():
    url = "ws://192.168.50.60:10000/api/generate/"

    async with connect(url) as websocket:
        jd = {
          "model": "llama3.2",
          "prompt": "Why is the sky blue?"
        }
        await websocket.send(json.dumps(jd))
        message = await websocket.recv()
        print(message)


if __name__ == "__main__":
    asyncio.run(hello())

