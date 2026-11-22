#!/usr/bin/env python3
"""Ask an LM Studio decision model using a YAML prompt."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from tools import make_headers, request_json

DEFAULT_URL = "http://192.168.50.60:1234"
DEFAULT_MODEL = "d1-omni-2b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", type=Path, help="YAML prompt file")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_URL)
    return parser.parse_args()


def load_prompt(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as prompt_file:
        prompt = yaml.safe_load(prompt_file)

    if not isinstance(prompt, dict):
        raise ValueError("Prompt must be a YAML object.")
    if not isinstance(prompt.get("state"), str):
        raise ValueError("Prompt must define a string 'state'.")
    questions = prompt.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("Prompt must define one or more 'questions'.")

    for question in questions.values():
        if not isinstance(question, dict):
            raise ValueError("Each question must be a YAML object.")
        if "instructions" not in question and "instruction" in question:
            question["instructions"] = question.pop("instruction")

    return prompt


def main() -> None:
    args = parse_args()
    try:
        prompt = load_prompt(args.prompt)
        message = input("> ")
        state = prompt["state"]
        if message:
            state = f"{state}\n\nUser message: {message}"
        payload = {
            "model": args.model,
            "state": state,
            "questions": prompt["questions"],
        }
        result = request_json(
            f"{args.base_url.rstrip('/')}/v1/systemone",
            make_headers(),
            payload,
        )
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()
