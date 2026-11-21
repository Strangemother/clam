#!/usr/bin/env python3
"""List loaded LM Studio decision models or ask one a question."""

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools import *

DEFAULT_URL = "http://192.168.50.60:1234"
DEFAULT_CONTEXT = (
    "Select from one of these internal routes."
)
DEFAULT_QUESTION = "Turn on the light"
ROUTING_CHOICES = {
    "lightbulb": "Control the lights",
    "heater": "Control the heating",
    "door": "Control the door",
    "memory": "store memories",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", help="loaded decision model ID")
    parser.add_argument(
        "question", nargs="?", default=DEFAULT_QUESTION,
        help="question to ask",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="list loaded decision model IDs",
    )
    parser.add_argument(
        "--context", default=DEFAULT_CONTEXT,
        help="context for the decision model",
    )
    parser.add_argument("--base-url", default=DEFAULT_URL)
    args = parser.parse_args()
    if not args.list_models and not args.model:
        parser.error("provide a model ID or use --list-models")
    return args


def example_select():
    answer = ask_decision_model(
        args.model,
        args.context,
        args.question,
        ROUTING_CHOICES,
        base_url,
        headers,
    )
    
def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    headers = make_headers()

    try:
        if args.list_models:
            model_ids = list_loaded_decision_models(base_url, headers)
            print("\n".join(model_ids))
            return

        answer = ask_decision_model(
            args.model,
            args.context,
            args.question,
            ROUTING_CHOICES,
            base_url,
            headers,
        )
        
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(answer, indent=2))


if __name__ == "__main__":
    main()
