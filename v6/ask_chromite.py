#!/usr/bin/env python3
"""Choose Chromite abilities from an environment or pet-owner message."""

import argparse
import json
import sys
from typing import Any

from tools import (
    list_loaded_decision_models,
    make_headers,
    request_json,
)

DEFAULT_URL = "http://192.168.50.60:1234"
ABILITY_THRESHOLD = 0.5
CHROMITE_CONTEXT = """\
You are Chromite, a small tadpole creature living in a tiny world.
Choose every ability that is useful for responding to the environment
description or pet owner's message. Abilities are evaluated independently.
A probability of 0.5 or higher selects that ability. An empty set is valid.

Abilities:
- remember: store a persistent memory
- forget: remove a persistent memory
- chill: relax or do nothing
- roam: wander the scene and gather insight
- track: focus on an entity
"""
ABILITY_QUESTIONS = {
    "remember": "Is there a durable fact worth storing as a memory?",
    "forget": "Should an existing memory be removed?",
    "chill": "Is relaxing or doing nothing the best response?",
    "roam": "Would exploring the scene help Chromite respond?",
    "track": "Is there an entity Chromite should focus on?",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", help="loaded decision model ID")
    parser.add_argument(
        "message", nargs="?",
        help="message from the pet owner",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="list loaded decision model IDs",
    )
    parser.add_argument(
        "--context", default="",
        help="environment description for Chromite",
    )
    parser.add_argument("--base-url", default=DEFAULT_URL)
    args = parser.parse_args()
    if not args.list_models and not args.model:
        parser.error("provide a model ID or use --list-models")
    if (
        not args.list_models
        and not args.context
        and not args.message
    ):
        parser.error("provide an environment description or pet-owner message")
    return args


def ask_chromite(
    model_id: str,
    context: str,
    message: str,
    base_url: str,
    headers: dict[str, str],
) -> list[str]:
    state_parts = [CHROMITE_CONTEXT]
    if context:
        state_parts.append(f"Environment description: {context}")
    if message:
        state_parts.append(f"Pet owner's message: {message}")

    payload = {
        "model": model_id,
        "state": "\n\n".join(state_parts),
        "questions": {
            ability: {
                "type": "noul",
                "instructions": question,
            } for ability, question in ABILITY_QUESTIONS.items()
        },
    }
    result = request_json(
        f"{base_url}/v1/systemone",
        headers,
        payload,
    )
    if not isinstance(result, dict) or not isinstance(
        result.get("answers"), dict
    ):
        raise RuntimeError("LM Studio returned an unexpected answer format.")

    answers: dict[str, Any] = result["answers"]
    selected = []
    for ability in ABILITY_QUESTIONS:
        answer = answers.get(ability)
        if not isinstance(answer, dict) or answer.get("type") != "noul":
            raise RuntimeError(
                f"LM Studio returned an invalid answer for {ability!r}."
            )
        probability = answer.get("noul")
        if (
            isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not 0 <= probability <= 1
        ):
            raise RuntimeError(
                f"LM Studio returned an invalid probability for {ability!r}."
            )
        if probability >= ABILITY_THRESHOLD:
            selected.append(ability)
    return selected


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    headers = make_headers()

    try:
        if args.list_models:
            model_ids = list_loaded_decision_models(base_url, headers)
            print("\n".join(model_ids))
            return

        abilities = ask_chromite(
            args.model,
            args.context,
            args.message or "",
            base_url,
            headers,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(abilities, indent=2))


if __name__ == "__main__":
    main()
