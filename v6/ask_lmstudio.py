#!/usr/bin/env python3
"""List loaded LM Studio decision models or ask one a question."""

import argparse
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_URL = "http://192.168.50.60:1234"
DEFAULT_STATE = (
    "I was charged twice this month. Please refund one of the charges."
)
DEFAULT_QUESTION = "Is the customer asking for a refund?"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", help="LM Studio model ID")
    parser.add_argument(
        "question", nargs="?",
        help="question to ask (defaults to the refund example)",
    )
    parser.add_argument(
        "--list-models", action="store_true", help="list available model IDs",
    )
    parser.add_argument(
        "--state", default=DEFAULT_STATE, help="context for the decision model",
    )
    parser.add_argument(
        "--chat", action="store_true", help="use a regular chat model instead",
    )
    parser.add_argument("--base-url", default=DEFAULT_URL)
    args = parser.parse_args()

    headers = {"Accept": "application/json"}
    token = os.environ.get("LM_STUDIO_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    base_url = args.base_url.rstrip("/")
    if args.list_models:
        path = "/v1/models" if args.chat else "/api/v1/models"
        request = Request(f"{base_url}{path}", headers=headers)
    else:
        if not args.model:
            parser.error("provide a model ID or use --list-models")
        question = args.question or DEFAULT_QUESTION
        if args.chat:
            path = "/v1/chat/completions"
            if args.question is None:
                question = (
                    f"Customer message: {args.state}\n\n"
                    f"Question: {question} Answer only Yes or No."
                )
            payload = {
                "model": args.model,
                "messages": [{"role": "user", "content": question}],
            }
        else:
            path = "/v1/systemone"
            payload = {
                "model": args.model,
                "state": args.state,
                "questions": {
                    "answer": {"type": "noul", "instructions": question},
                },
            }
        headers["Content-Type"] = "application/json"
        request = Request(
            f"{base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )

    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace").strip()
        parser.exit(1, f"{path}: HTTP {exc.code}: {detail or exc.reason}\n")
    except OSError as exc:
        parser.exit(1, f"Could not reach LM Studio at {base_url}: {exc}\n")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        parser.exit(1, f"LM Studio did not return valid JSON: {exc}\n")

    try:
        if args.list_models:
            if args.chat:
                models = [model["id"] for model in result["data"]]
            else:
                models = [
                    instance["id"]
                    for model in result["models"]
                    if model["type"] == "decision"
                    for instance in model["loaded_instances"]
                ]
                if not models:
                    parser.exit(
                        1, f"No loaded decision models found at {base_url}. "
                        "Check the Developer tab on that LM Studio server.\n",
                    )
            print("\n".join(models) if models else "No models returned.")
        elif args.chat:
            answer = result["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                parser.exit(1, "LM Studio returned no text answer.\n")
            print(answer.strip())
        else:
            print(json.dumps(result["answers"]["answer"], indent=2))
    except (IndexError, KeyError, TypeError):
        parser.exit(1, "LM Studio returned an unexpected response format.\n")


if __name__ == "__main__":
    main()
