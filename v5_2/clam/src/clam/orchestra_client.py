"""Minimal backbone service to track active units."""
from datetime import datetime, timezone
import socket
import uuid

def main(args=None):
    """Run the backbone service."""
    import argparse

    if args is None:
        parser = argparse.ArgumentParser(description="Backbone service")
        configure_parser(parser)
        args = parser.parse_args()

    P = args.filepath
    if args.prompt is not None:
        P = f'{args.prompt_dir}/{args.prompt}.prompt.md'

    ChatClient(
        port=args.port,
        backbone_url='http://localhost:5000/',
        id=args.id,
        name=args.name or args.prompt,
        prompt=P
    ).run()


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


def configure_parser(parser, subparsers=None):
    """Configure the subparser for backbone service."""

    if subparsers:
        parser = subparsers.add_parser('client', help='Run the client service')
    parser.set_defaults(func=main)

    parser.add_argument('--id', default=None, type=str)
    parser.add_argument('--name', default=None, type=str)
    parser.add_argument('--port', default=0, type=int)


    parser.add_argument('--prompt-dir', default="../../prompts", type=str)
    parser.add_argument('--prompt', default=None, type=str)
    parser.add_argument('--filepath', default=None, type=str)

    return parser



if __name__ == '__main__':
    main()
