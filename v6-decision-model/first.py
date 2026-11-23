#!/usr/bin/env python3
"""Ask an LM Studio decision model using a YAML prompt."""

import argparse
import sys
from pathlib import Path

import yaml

from prompt_utils import load_prompt
from tools import make_headers, request_json

# DEFAULT_URL = "http://192.168.50.60:1234"
DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_MODEL = "d1-omni-2b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", type=Path, help="YAML prompt file")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_URL)
    parser.add_argument(
        "--live-file",
        action="store_true",
        help="reload the YAML prompt before each request",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="ask once, then exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        prompt = load_prompt(args.prompt)
        print(f"State:\n{prompt['state']}\n")
        example_index = 0
        while True:
            if args.live_file:
                prompt = load_prompt(args.prompt)
            examples = prompt["examples"]
            if examples:
                example_index %= len(examples)
                prompt_text = f"(example#{example_index + 1}) > "
            else:
                prompt_text = "> "
            try:
                message = input(prompt_text)
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not message.strip() and not examples:
                break
            if not message.strip():
                message = examples[example_index]
                example_index = (example_index + 1) % len(examples)
                print(message, end="\n\n")
            payload = {
                "model": args.model,
                "state": (
                    f"{prompt['state']}\n\nUser message: {message}"
                ),
                "questions": prompt["questions"],
            }
            result = request_json(
                f"{args.base_url.rstrip('/')}/v1/systemone",
                make_headers(),
                payload,
            )
            print(
                yaml.safe_dump(
                    result,
                    sort_keys=False,
                    indent=4,
                ),
                end="",
            )
            if args.once:
                break
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
