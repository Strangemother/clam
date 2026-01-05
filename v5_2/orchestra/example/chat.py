"""Example chat client, to _initiate_ a prompt and
respond on the port for job.

    python chat.py --prompt announcer
    Reserving Port: 0
    Socket running at http://0.0.0.0:60385
    Serving on 0.0.0.0:60385

Then send messages to it through a post
---

exapanded:

    c:/Users/jay/Documents/projects/js-peer-to-peer-audio/env/Scripts/python
    chat.py --prompt announcer
"""

from orchestra.client import Client
import time
import argparse

from clam.prompt import Prompt


from clam.terminal_client import TerminalClient
import pathlib

HERE =  pathlib.Path(__file__).parent


class ChatClient(Client):

    def __init__(self, *a, **kwargs):
        super().__init__(*a, **kwargs)
        self.setup()

    def setup(self):
        self.prompt = Prompt(HERE / self.kwargs.get('prompt'))
        self.tc = TerminalClient(self.prompt)
        print('setup tc', self.tc)

    def process_job(self, job):
        n = self.kwargs.get('name', self.__class__.__name__)
        print(f"[{n}] Got job: {job}")
        tc = self.tc
        res = tc.append_input(job.decode('utf'))
        text = tc.get_clean_response_message_content(res)
        print('\n\nAnswer:', text, '\n\n')
        # time.sleep(2)
        # return bytes("I like butterscotch.", 'utf-8')
        # return str({'echo': job})
        # return bytes(str(int(bytes(job)) + 2), 'utf')
        return text


parser = argparse.ArgumentParser(description="Clam Client")
parser.add_argument('--id', default=None, type=str)
parser.add_argument('--name', default=None, type=str)
parser.add_argument('--port', default=0, type=int)

parser.add_argument('--prompt', default=None, type=str)
parser.add_argument('--filepath', default=None, type=str)

ns, unknown = parser.parse_known_args()

P = ns.filepath
if ns.prompt is not None:
    P = f'../../prompts/{ns.prompt}.prompt.md'

if __name__ == '__main__':

    ChatClient(
        port=ns.port,
        backbone_url='http://localhost:5000/',
        id=ns.id,
        name=ns.name or ns.prompt,
        prompt=P
    ).run()
