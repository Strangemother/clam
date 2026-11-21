#!/usr/bin/env python3
"""List LM Studio models or ask one a question using the standard library."""

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_URL = "http://192.168.50.60:1234"
DEFAULT_QUESTION = (
    "Customer message: I was charged twice this month. "
    "Please refund one of the charges.\n\n"
    "Question: Is the customer asking for a refund? Answer only Yes or No."
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", help="LM Studio model ID")
    parser.add_argument(
        "question", nargs="?", default=DEFAULT_QUESTION,
        help="question to ask (defaults to the refund example)",
    )
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--base-url", default=DEFAULT_URL)
    args = parser.parse_args()

    headers = {"Accept": "application/json"}
    token = os.environ.get("LM_STUDIO_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    base_url = args.base_url.rstrip("/")
    if args.list_models:
        request = Request(f"{base_url}/v1/models", headers=headers)
    else:
        if not args.model:
            parser.error("provide a model ID or use --list-models")
        payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": args.question}],
        }
        headers["Content-Type"] = "application/json"
        request = Request(
            f"{base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )

    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        parser.exit(1, f"LM Studio returned HTTP {exc.code}: {exc.reason}\n")
    except (OSError, URLError) as exc:
        parser.exit(1, f"Could not reach LM Studio at {base_url}: {exc}\n")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        parser.exit(1, f"LM Studio did not return valid JSON: {exc}\n")

    try:
        if args.list_models:
            models = [model["id"] for model in result["data"]]
            print("\n".join(models) if models else "No models returned.")
        else:
            answer = result["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                parser.exit(1, "LM Studio returned no text answer.\n")
            print(answer.strip())
    except (IndexError, KeyError, TypeError):
        parser.exit(1, "LM Studio returned an unexpected response format.\n")


if __name__ == "__main__":
    main()
