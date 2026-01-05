"""Post a message to a client

    $>clam post --port 63067 "postitve_electrode enabled"
    Loading config config.py
    {"count":1,"job_id":"3a0cacf3-a831-436e-89a4-1b2a67d71c3c","ok":true}

"""
import pathlib
import argparse
import requests


HERE =  pathlib.Path(__file__).parent


def main(args=None):
    """Run the backbone service."""

    if args is None:
        parser = argparse.ArgumentParser(description="Backbone service")
        configure_parser(parser)
        args = parser.parse_args()

    url = f'http://127.0.0.1:{args.port}/job'

    res = requests.post(url,
        data=bytes(args.text, 'utf'),
        timeout=3,
        # headers=headers
    )
    print(res.text)


def configure_parser(parser, subparsers=None):
    """Configure the subparser for backbone service."""

    if subparsers:
        parser = subparsers.add_parser('post', help='post to client tool')
    parser.set_defaults(func=main)

    parser.add_argument('--port', default=9202, type=int)
    parser.add_argument('text', default='I like butterscotch', type=str)

    # parser.add_argument('--prompt-dir', default="../../prompts", type=str)
    # parser.add_argument('--prompt', default=None, type=str)
    # parser.add_argument('--filepath', default=None, type=str)

    return parser



if __name__ == '__main__':
    main()
