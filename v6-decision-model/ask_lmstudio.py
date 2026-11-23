#!/usr/bin/env python3
"""List loaded LM Studio decision models or ask one a question."""

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_URL = "http://192.168.50.60:1234"
DEFAULT_CONTEXT = (
    "Select from one of these internal routes: lightbulb, heater, door."
)
DEFAULT_QUESTION = "Turn on the light"
ROUTING_CHOICES = {
    "lightbulb": "Control the lights",
    "heater": "Control the heating",
    "door": "Control the door",
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


def make_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = os.environ.get("LM_STUDIO_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> Any:
    request_headers = headers.copy()
    data = None
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=request_headers)

    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"{url}: HTTP {exc.code}: {detail or exc.reason}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Could not reach LM Studio: {exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        message = f"LM Studio did not return valid JSON: {exc}"
        raise RuntimeError(message) from exc


def list_loaded_decision_models(
    base_url: str,
    headers: dict[str, str],
) -> list[str]:
    result = request_json(f"{base_url}/api/v1/models", headers)
    if not isinstance(result, dict) or not isinstance(
        result.get("models"), list
    ):
        raise RuntimeError("LM Studio returned an unexpected model list.")

    model_ids = []
    for model in result["models"]:
        if not isinstance(model, dict) or model.get("type") != "decision":
            continue
        instances = model.get("loaded_instances", [])
        if not isinstance(instances, list):
            continue
        model_ids.extend(
            instance["id"]
            for instance in instances
            if isinstance(instance, dict)
            and isinstance(instance.get("id"), str)
        )

    if not model_ids:
        raise RuntimeError(
            f"No loaded decision models found at {base_url}. "
            "Check the Developer tab on that LM Studio server."
        )
    return model_ids


def ask_decision_model(
    model_id: str,
    context: str,
    question: str,
    base_url: str,
    headers: dict[str, str],
) -> Any:
    payload = {
        "model": model_id,
        "state": context,
        "questions": {
            "route": {
                "type": "choice",
                "instructions": question,
                "criteria": ROUTING_CHOICES,
            },
        },
    }
    result = request_json(
        f"{base_url}/v1/systemone",
        headers,
        payload,
    )
    if not isinstance(result, dict) or not isinstance(
        result.get("answers"), dict
    ) or "route" not in result["answers"]:
        raise RuntimeError("LM Studio returned an unexpected answer format.")
    return result["answers"]["route"]


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
            base_url,
            headers,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(answer, indent=2))


if __name__ == "__main__":
    main()
