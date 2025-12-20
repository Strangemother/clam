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
from . import config
from .services import get_service_endpoint
from .backbone import get_backbone_url



from .prompt import Prompt
from .terminal_select import select_prompt

import argparse


HERE =  pathlib.Path(__file__).parent


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


def configure_parser(parser, subparsers):
    """Configure the subparser for terminal chat."""
    parser_cli = parser
    if subparsers:
        parser_cli = subparsers.add_parser("cli",
                                       help="Run terminal chat")
    parser_cli.set_defaults(func=main)
    parser_cli.add_argument("name",
                           type=str,
                           nargs='?',
                           # required=False,
                            help="User prompt name"
                    )

    parser_cli.add_argument("--prompt-file", "-f",
                           type=str,
                           required=False,
                            help="User prompt text"
                    )

    parser_cli.add_argument("--id",
                           type=str,
                           default=None,
                           required=False,
                    )
    parser_cli.add_argument("--select", "-s",
                           type=str,
                           nargs='?',
                           const='select',
                           help="Select prompt from directory (optionally specify directory)")


def main(args=None):
    cwd = os.getcwd()
    if args is None:
        parser = argparse.ArgumentParser(
            description="Simple CLI for passing a prompt to a bot"
        )
        configure_parser(parser)
        args = parser.parse_args()

    pf = args.prompt_file
    _id = args.id

    if pf is None:
        pf = config.DEFAULT_PROMPT_FILE
        if args.name is not None:
            pf = f'prompts/{args.name}.prompt.md'
            print('Loading', pf)

    # Handle prompt selection
    if hasattr(args, 'select') and args.select:
        prompt_dir = args.select if args.select != 'select' else None
        pf = select_prompt(prompt_dir)
        if pf is None:
            print("No prompt selected. Exiting.")
            return
    # else:
        # pf = args.prompt_file
        # if pf is None:
        #     pf = config.DEFAULT_PROMPT_FILE

    print("Loading file:", pf, end='')
    pr = Prompt(pathlib.Path(cwd) / pf)

    print(f' "{pr.title}": using model {pr.model}')

    data = setup_structure(pr)
    mount_backbone({
        "name": pr.title,
        "type": "terminal_chat",
        "id": _id,
        # "url": "http://terminal_chat.local"
    })

    register_unmount()

    is_convo = pr.type == 'conversation'
    print('is_convo', is_convo)

    if is_convo:
        out = continue_conversation(data)
        graph_dispatch(_id, data, out)
        print_response(out)
        data['messages'].append(out['choices'][0]['message'])
    prime_loop(pr, is_convo, data, _id)


def prime_loop(pr, is_convo, data, _id):
    try:
        primary_query_loop(pr, is_convo, data, _id)
    except KeyboardInterrupt:
        print('! unlooped. Insert commands')
        command_loop(pr, is_convo, data, _id)


def command_loop(pr, is_convo, data, _id):
    ok = 1
    while ok:
        inp = input('# ')
        ok = parse_command(pr, inp, is_convo, data, _id)


def parse_command(pr, inp, is_convo, data, _id):
    print('parse', inp)
    val = inp.strip().lower()

    commands = {
        "continue": command_continue,
        "quit": command_quit,
        "reload": command_reload,
        "update": command_update,
    }

    for k in commands:
        if (k).startswith(val):
            print('executing', k)
            ok = commands[k](pr, inp, is_convo, data, _id)
            return ok

    print('Unknown command. Choices:', tuple(commands.keys()))
    return command_loop(pr, is_convo, data, _id)


def command_quit(pr, inp, is_convo, data, _id):
    """Quit the terminal"""
    return False


def command_continue(pr, inp, is_convo, data, _id):
    """continue back into chat mode"""
    return prime_loop(pr, is_convo, data, _id)


def command_reload(pr, inp, is_convo, data, _id):
    """ RELOAD the conversation, new converation chain with no messages and
    and updated system prompt """
    data = setup_structure(pr)
    return prime_loop(pr, is_convo, data, _id)


def command_update(pr, inp, is_convo, data, _id):
    """ UPDATE the conversation, the same messages and and updated system prompt """



def primary_query_loop(pr, is_convo, data, _id):
    while True:
        inp = input('> ')
        msg = as_message(inp)


        if is_convo:
            data['messages'].append(msg)
            out = continue_conversation(data)
            graph_dispatch(_id, data, msg)
            print_response(out)
            data['messages'].append(out['choices'][0]['message'])
        else:
            # only the first system then user
            nd = setup_structure(pr)
            nd['messages'][0]['content'] = pr.render(message=msg)
            nd['messages'].append(msg)
            out = continue_conversation(nd)
            graph_dispatch(_id, nd, msg)
            print_response(out)

# Store the unit ID globally for unmount
_unit_id = None


def mount_backbone(registration=None):
    """Tell the backbone service this unit is awake."""
    global _unit_id
    from . import backbone
    _unit_id = backbone.mount(registration)
    return _unit_id


def register_unmount():
    """Register an atexit handler to unmount from backbone."""
    import atexit
    from . import backbone

    def _unmount():
        if _unit_id:
            backbone.unmount(_unit_id)

    atexit.register(_unmount)


def continue_conversation(res):
    endpoint = get_service_endpoint('completions')
    resp =  _post(endpoint, {
            # 'model':'TinyDolphin',
            # model='phi4:latest',
            # 'prompt':'enumerate and list every number from 200 to 1000.',
            # **tool_prompt()
            **res
    })

    return resp


def graph_dispatch(client_id, result, message, sender_url=None, response_id=None):
    """Send this message to the graph tool if graphed.
    """
    # post to backbone
    backbone = get_backbone_url()
    url = f"{backbone}/graph-response"
    print('send to graph', url)
    res = requests.post(url, json={
            'result': result,
            'message': message,
            'id': response_id,
            'sender_url': sender_url,
            'client_id': client_id,
        })

    print('result from backbone:', res)


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


# async def hello(data=None):
#     data = data or setup_structure()
#     resp = await _post(hurl, {
#             # 'model':'TinyDolphin',
#             # model='phi4:latest',
#             # 'prompt':'enumerate and list every number from 200 to 1000.',
#             # **tool_prompt()
#             **data
#     })

#     print(resp)
#     return resp


from clam.tooler import create_tool_definition


def kitchen_heater(state:bool):
    """Turn the kitchen header on/off

    arguments:
        state: Switch state of the heater. True == on

    """
    print('Run code.')



def setup_structure(system_prompt):
    res = {
      # "model": "llama3.2:latest",
      # "model": "granite-4.0-h-350m-unsloth-hybrid",
      "messages": [
            {
                "role": "system",
                "content": system_prompt.content
            },
            # {
            #   "role": "user",
            #   # "content": "Follow the white rabbit?"
            #   "content": "What is your favourite fruit? Please answer in one word"
            # }
        ],
        "stream": False,
        'tools': [create_tool_definition(kitchen_heater)]
    }
    if isinstance(system_prompt, Prompt):
        model = system_prompt.model
        if model:
            res['model'] = model
    return res

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
