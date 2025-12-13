"""CLI entry point for clam commands."""
import argparse

from .terminal_chat import (configure_parser as configure_terminal_chat,
                            main as terminal_main)
from .backbone import (configure_parser as configure_backbone,
                      main as backbone_main)


def main():
    parser = argparse.ArgumentParser(description="Clam CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # cli subcommand
    configure_terminal_chat(parser, subparsers)

    # backbone subcommand
    configure_backbone(parser, subparsers)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
