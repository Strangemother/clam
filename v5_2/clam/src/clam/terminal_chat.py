"""Talk to the LLM on the terminal.
"""
import os
import requests
import asyncio
# from websockets.asyncio.client import connect
# from websockets.sync.client import connect
import json
from pprint import pprint
import pathlib


HERE =  pathlib.Path(__file__).parent

hurl = "http://192.168.50.60:1234/v1/chat/completions/"
# hurl = "http://192.168.50.60:10000/api/generate/"


def _post(url, payload, print_out=False):

    headers = {
        'Content-Type': "application/json",
        # 'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    data = json.dumps(payload)
    print('post', url)
    if print_out:
        for msg in payload['messages']:
            # print('  >  ', f"{msg['role']:<12} {msg['content']}")
            print_response(msg)
    response = requests.request("POST", url, data=data, headers=headers, stream=True)
    # print('\nResponse:')
    data = response.json()
    return data
    # print(data['choices'][0]['message'])
    # print(data['choices'][0]['message']['content'])


from .prompt import Prompt

import argparse

def make_parser():
    parser = argparse.ArgumentParser(
        description="Simple CLI for passing a prompt to a bot"
    )

    parser.add_argument("--prompt-file", "-f", type=str, required=False,
                        help="User prompt text"
                    )

    return parser


def main():
    cwd = os.getcwd()
    parser = make_parser()
    args = parser.parse_args()
    pf = args.prompt_file
    if pf is None:
        pf = 'prompts/angry-bot.prompt.md'
    print("Loading file:", pf, end='')
    pr = Prompt(pathlib.Path(cwd) / pf)

    print(f' "{pr.title}"')

    data = setup_structure(pr)
    mount_backbone()
    out = continue_conversation(data)
    print_response(out)
    data['messages'].append(out['choices'][0]['message'])

    while True:
        inp = input('> ')
        msg = as_message(inp)

        data['messages'].append(msg)
        out = continue_conversation(data)
        print_response(out)
        data['messages'].append(out['choices'][0]['message'])


def mount_backbone():
    # Tell the backbone service this unit is awake.
    print('Tell backbone')


def continue_conversation(res):
    resp =  _post(hurl, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # **tool_prompt()
            **res
    })

    return resp


def print_response(data):
    if 'choices' in data:
        msg = data['choices'][0]['message']
        role = msg.get('role')
        print(f"{role:<12} {msg['content']}")
    else:
        try:
            msg = data['content']
        except KeyError:
            print(data)
            return
        role = data.get('role', 'unknown')
        print(f"{role:<12} {msg}")


def as_message(res):
    msg = { "role": "user", "content": res}
    return msg


def append_input(data, res):
    msg = { "role": "user", "content": res }
    data['messages'].append(msg)
    return msg


def append_output(data, out):
    data['messages'].append(out)




async def hello(data=None):
    data = data or setup_structure()
    resp = await _post(hurl, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # **tool_prompt()
            **data
    })

    print(resp)
    return resp


def setup_structure(system_prompt):
    return {
      # "model": "llama3.2:latest",
      # "model": "granite-4.0-h-350m-unsloth-hybrid",
      "model": system_prompt.model, #"granite-4.0-h-tiny",
      "messages": [
            {
                "role": "system",
                "content": system_prompt.content
            },
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
    main()
