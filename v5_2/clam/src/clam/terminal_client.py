"""Similar to chat, but classy and hooked.

- for user chat to prompt
- for prompt to prompt
- with data objects
- graph based switching loop
- stream or term based
- templated in/out/save
- multi-model (two requests at once.)
- multi-response (url based)

Run terminal to terminal:

    python -m clam.terminal_client lightbulb-hacker -g ./prompts/lightbulb.prompt.md

"""

import os
import requests
import json
import pathlib
import argparse
from pprint import pprint as pp

import time

from . import config
from . import backbone
from .prompt import Prompt
from .services import get_service_endpoint,do_key
from .terminal_select import select_prompt
from .tooler_bot import get_tools
from . import voice_proc

HERE =  pathlib.Path(__file__).parent


def configure_parser(parser, subparsers=None):
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
    parser_cli.add_argument("--child-prompt-file", "-g",
                            type=str,
                           required=False,
                            help="Child prompt text"
                    )

    parser_cli.add_argument("--model", "-m",
                           type=str,
                           required=False,
                            help="Apply or overide the prompt model"
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

    parser_cli.add_argument("--context", "-c",
                           type=pathlib.Path,
                           nargs='?',
                           help="add data files")


def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(
            description="Simple CLI for passing a prompt to a bot"
        )
        configure_parser(parser)
        args = parser.parse_args()
    if args.child_prompt_file:
        parent_chat(args)
    else:
        simple_chat(args)


def simple_chat(args):
    """The user (termnial input) communicates directly to the model,
    using the loaded prompt as the system message.
    """
    pr = get_prompt_file(args)
    if pr: print(f' "{pr.title}"')

    ctx = get_context(args)
    _id = args.id
    tc = SpokenTerminalClient(pr, model=args.model,
                        template_context=ctx,
                        client_id=_id)

    return tc.loop()


def get_context(args):
    ctx = {}
    if args.context:
        if os.path.exists(args.context):
            ctx = json.loads(args.context.read_text())
    return ctx


def parent_chat(args):
    """Load the prompt as the primary model, and send messages to another
    prompt, acting as the user.

    This allows a model loaded with a "parent" prompt to send and recieve to the
    "child" prompt.

        Parent (prompt A) Be chatty
        Child (Prompt B) Be stuborn

        Parent: "Hello"
        Child: "No"
        Parent: "Okay"

    """
    pr = get_prompt_file(args)
    if pr: print(f' "{pr.title}"')

    ctx = get_context(args)
    parent = TerminalClient(pr, model=args.model, template_context=ctx)

    pr = get_prompt_file(args, 'child_prompt_file')
    if pr: print(f' "{pr.title}"')

    child = TerminalClient(pr, model=args.model, template_context=ctx)

    # PArent is ready. first message from the parent is piped to the client.
    parent_query_data = parent.not_loop()
    parent_msg = parent.get_clean_response_message_content(parent_query_data)

    while parent.running:

        print('\n\n --- \n\n')
        res = child.append_input(parent_msg)
        child_content = child.print_response(res)
        child_msg = child.get_clean_response_message_content(child_content)

        time.sleep(1)
        print('\n\n --- \n\n')
        res = parent.append_input(child_msg)
        parent_content = parent.print_response(res)
        parent_msg = parent.get_clean_response_message_content(parent_content)


def get_prompt_file(args, key='prompt_file'):
    pf = getattr(args, key)
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
    cwd = os.getcwd()
    pr = Prompt(pathlib.Path(cwd) / pf)
    return pr

    # data = setup_structure(pr)
    # mount_backbone({
    #     "name": pr.title,
    #     "type": "terminal_chat",
    #     "id": _id,
    #     # "url": "http://terminal_chat.local"
    # })

    # register_unmount()

    # is_convo = pr.type == 'conversation'
    # print('is_convo', is_convo)

    # if is_convo:
    #     out = continue_conversation(data)
    #     graph_dispatch(_id, data, out)
    #     print_response(out)
    #     data['messages'].append(out['choices'][0]['message'])
    # prime_loop(pr, is_convo, data, _id)


class TerminalClientBase:
    pass


class TerminalClient(TerminalClientBase):

    running = True
    model = None
    save = True
    first_shot = False
    one_shot = None

    # replace "assistant" with the name of the prompt e.g. "kettle"
    role_replace = True
    backbone = True

    def __init__(self, prompt=None, model=None, template_context=None, client_id=None):
        self._id = client_id
        self.prompt = prompt
        self.model = model or self.model
        self.template_context = template_context or {}
        self._filekey = None
        self.set_input_func()

        self.input_ind = '>'
        self.commander_input_ind = '#'
        self.conversation = self.setup_structure()

    def set_input_func(self, func=None):
        if func is None:
            func = self.loop_conversation
        self.input_func = func

    def load_conversation(self):
        # pickup an asset as a history to use as structure.
        pass

    def get_conversation(self):
        return self.conversation

    def get_template_context(self):
        return self.template_context

    def setup_structure(self, system_prompt=None):
        system_prompt = system_prompt or self.prompt
        d = self.get_template_context()
        res = {
          # "model": "llama3.2:latest",
          # "model": "granite-4.0-h-350m-unsloth-hybrid",
          "messages": [
                {
                    "role": "system",
                    "content": system_prompt.render(**d)
                },
                # {
                #   "role": "user",
                #   # "content": "Follow the white rabbit?"
                #   "content": "What is your favourite fruit? Please answer in one word"
                # }
            ],
            # "reasoning": { "effort": "low" },
            # "temperature": .8,
            # "max_tokens": -1,

            # "top_p": 1,
            # "top_k": 1,
            # "temperature": 1,
            # "max_tokens": 1,
            ## "stop": 1,
            # "presence_penalty": 1,
            # "frequency_penalty": 1,
            # "logit_bias": 1,
            # "repeat_penalty": 1,
            # "seed": 1,
            "stream": False,

        }

        if isinstance(system_prompt, Prompt):
            model = system_prompt.model
            tools = self.collect_tools(system_prompt)
            if tools:
                res['tools'] = tools
        if self.model is not None:
            # terminal and class override prompt file.
            model = self.model

        if model:
            res['model'] = model

        return res

    def collect_tools(self, prompt):
        """Read from front matter"""
        return get_tools(prompt.raw_meta.get('tools'))

    def load_prompt(self, prompt):
        pass

    def loop(self):
        """Run the user input loop, using the graphed function
        for the target _layer_.
        """
        if self.backbone:
            self.backbone = self.mount_backbone()
        if self.first_shot:
            self.dispatch()
        while self.running:
            _ans = self.input_func()
        print('Session end.')

    def not_loop(self, inp=None):
        """Run the user input loop, using the graphed function
        for the target _layer_.
        """
        _ans = None
        if self.first_shot:
            _ans = self.dispatch()
        if inp:
            _ans = self.append_input(inp)
            return _ans
        print('Session answer.')
        return _ans

    def append_input(self, inp):
        return self.handle_input(inp)

    def loop_conversation(self):
        """ Input and continue
        """
        try:
            inp = input(f'{self.input_ind} ')
            return self.handle_input(inp)
        except KeyboardInterrupt:
            print('! command mode, perform CTRL+C to exit')
            self.input_func = self.loop_commander
            # self.running = False

    def loop_commander(self):
        """ Input commands and continue
        """
        try:
            inp = input(f'{self.commander_input_ind} ')
            return self.handle_command(inp)
        except KeyboardInterrupt:
            print('! command mode exit')
            self.running = False

    def handle_command(self, inp):
        """The user input a message. Dispatch it as
        a conversation.
        """
        print(f'Command: {inp}')
        val = inp.strip().lower()
        commands = self.get_commands()

        # commands = {
        #     "continue": self.command_continue,
        #     "quit": self.command_quit,
        # }

        for k in commands:
            if k.startswith(val):
                print('executing', k)
                return commands[k](val)


        print('Unknown command')
        self.command_help()

    def get_commands(self):
        return {
            x[8:]: getattr(self, x) for x in dir(self) if x.startswith('command_')
        }

    def command_continue(self, val=None):
        self.set_input_func()

    def command_quit(self, val=None):
        self.running = False

    def command_help(self, val=None):
        commands = self.get_commands()
        print('Choices:', tuple(commands.keys()))

    def handle_input(self, inp):
        """The user input a message. Dispatch it as
        a conversation.
        """
        print(f'In: {inp}')
        msg = self.as_message(inp)
        return self.dispatch(msg)

    def dispatch(self, msg=None):
        data = self.get_conversation()
        if msg:
            data['messages'].append(msg)

        self.save_pre_post(data)
        resp = self.continue_conversation(data)
        content = self.store_response(data, resp)

        self.print_response(content)
        return content

    def save_pre_post(self, data):
        """Save the conversation before the post to the endpoint,
        """
        pass

    def store_response(self, data, resp):
        """Store the response into the given data
        """
        if 'error' in resp:
            alt_resp = self.handle_error(resp)
            if alt_resp:
                resp = alt_resp

        if self.one_shot is not True:
            if 'choices' in resp:
                data['messages'].append(resp['choices'][0]['message'])
        else:
            print('.. is one-shot. Will not store response.')
        self.save_post_post(data, resp)
        return resp

    def save_post_post(self, data, resp):
        t = json.dumps(data, indent=4)
        filename = self._filekey or int(time.time())
        if self._filekey is None:
            self._filekey = filename

        p = pathlib.Path('./cache' ) / self.prompt.name / f"{filename}.json"
        ap = p.parent.absolute()
        if ap.exists() is False:
            os.makedirs(ap)
        p.write_text(t)

    def handle_error(self, resp):
        """
            {'error': {'code': None,
               'message': 'Multiple models are loaded.
                            Please specify a model by '
                          "providing a 'model' field.",
               'param': 'model',
               'type': 'invalid_request_error'}}
        """
        v = 'multiple models are loaded'
        try:
            m = resp['error']['message']
        except TypeError:
            m  = resp
            print('Error:', m)
            return resp
        if v in m.lower():
            print('    ERROR: Service needs a model...')
            self.model = self.get_default_model()
            data = self.get_conversation()
            data['model'] = self.model
            print('    attempting repair using defaults...')
            resp = self.continue_conversation(data)

        print('  Corrected response:')
        pp(resp)
        return resp

    def get_default_model(self):
        """Note model collection has a few layers.

        + prompt: the `model` key
        + cli: through the terminal switches
        + terminal class: The `self.model`
        + the service: default model

        By default we assume no `model` in the prompt meta.
        If the endpint returns an error _many models exist_,
        we need to select one.
        Here we can collect the _DEFAULT_PROMPT_ from the config.
        """
        return 'tiger-gemma-9b-v3'

    def as_message(self, res):
        msg = { "role": "user", "content": res}
        return msg

    def continue_conversation(self, res):
        endpoint = get_service_endpoint('completions')
        resp =  self._post(endpoint, {
                # 'model':'TinyDolphin',
                # model='phi4:latest',
                # 'prompt':'enumerate and list every number from 200 to 1000.',
                # **tool_prompt()
                **res
        })

        return resp

    def mount_backbone(self, registration=None):
        """Tell the backbone service this unit is awake."""

        registration = registration or {
            "name": self.prompt.title,
            "type": "terminal_chat",
            "id": self._id,
            # "url": "http://terminal_chat.local"
        }
        _unit_id = backbone.mount(registration)
        return _unit_id

    def print_response(self, data):
        choice = self.print_response_message(data)
        self.print_response_tools(data, choice)
        return choice

    def print_response_message(self, data):
        if 'choices' in data:
            msg = data['choices'][0]['message']
            role = msg.get('role')
            if self.role_replace:
                role = self.prompt.name
            print(f"{role:<12} {msg['content']}")
            return msg
        else:
            try:
                msg = data['content']

            except KeyError:
                print(data)
                return data
            role = data.get('role', 'unknown')
            print(f"{role:<12} {msg}")
            return msg

    def get_response_message(self, data):
        if 'choices' in data:
            msg = data['choices'][0]['message']
            return msg['content']
        else:
            try:
                msg = data['content']
            except KeyError:
                print('KeyError:', data)
                return data
            return msg

    def get_clean_response_message_content(self, data):
        v = self.get_clean_response_message(data)
        if isinstance(v, str):
            return v
        return v.get('content') or v

    def get_clean_response_message(self, data):
        if 'choices' in data:
            msg = data['choices'][0]['message']
            return msg

        try:
            msg = data['content']
        except KeyError:
            print(data)
            return data
        return msg

    def print_response_tools(self, data, choice):
        tool_calls = choice.get('tool_calls') or []
        for tool in tool_calls:
            name = tool['function']['name']
            print(f"{name}, ", end='')
            pp(json.loads(tool['function']['arguments']))
        print('.')

    def _post(self, url, payload, print_out=False):
        AGENT_ACCESS_KEY = do_key

        headers = {
            'Content-Type': "application/json",
            # 'Accept': "*/*",
            "Authorization":f"Bearer {AGENT_ACCESS_KEY}",
            'Cache-Control': "no-cache",
            }

        data = json.dumps(payload)
        print('  post', url)
        response = requests.request("POST", url, data=data, headers=headers, stream=True)
        # print('\nResponse:')
        data = response.json()
        return data
        # print(data['choices'][0]['message'])
        # print(data['choices'][0]['message']['content'])


class SpokenTerminalClient(TerminalClient):

    def store_response(self, data, resp):
        resp = super().store_response(data, resp)
        # send to speaker.
        d = self.get_response_message(resp)
        self.say(d)
        return resp

    def setup_throat(self):
        p, (parent_conn, child_conn) = voice_proc.start_worker()
        self.say_proc = p
        self.parent_conn = parent_conn
        self.child_conn = child_conn

    def loop(self):
        self.setup_throat()
        return super().loop()

    def say(self, value):
        self.parent_conn.send(value)


if __name__ == '__main__':
    main()