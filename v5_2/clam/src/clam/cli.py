"""CLI entry point for clam commands."""
import argparse

from .terminal_chat import (configure_parser as configure_terminal_chat,
                            main as terminal_main)
from .backbone import (configure_parser as configure_backbone,
                      main as backbone_main)
from . import config


def main():
    parser = argparse.ArgumentParser(description="Clam CLI")
    parser.add_argument('--config', help='Config file path')
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # cli subcommand
    configure_terminal_chat(parser, subparsers)
    configure_backbone(parser, subparsers)

    args = parser.parse_args()
    config.load(args.config)

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()


if __name__ == "__main__":
    main()
