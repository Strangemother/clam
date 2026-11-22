#!/usr/bin/env python3
"""Serve LiquidAI D1 Omni through a small Flask System One API.

Start the server on the model host from the v6 directory with
`python easy-run.py`. Replace HOST_IP below with that machine's LAN address.
Open `http://HOST_IP:8000/ui` to run a prompt example in the browser.

Check health and list the loaded model:

```python
import json
from urllib.request import urlopen

base_url = "http://HOST_IP:8000"
for path in ("/health", "/api/v1/models"):
    with urlopen(base_url + path) as response:
        print(json.dumps(json.load(response), indent=2))
```

Send a text-only decision request:

```python
import json
from urllib.request import Request, urlopen

base_url = "http://HOST_IP:8000"
payload = {
    "model": "d1-omni-2b",
    "state": "I was charged twice. Please refund one charge.",
    "questions": {
        "refund": {
            "type": "noul",
            "instructions": "Is the customer asking for a refund?",
        },
        "team": {
            "type": "choice",
            "instructions": "Which team should handle this?",
            "criteria": {
                "billing": "Charges and refunds",
                "shipping": "Delivery and parcels",
                "technical": "App or site faults",
            },
        },
    },
}
request = Request(
    f"{base_url}/v1/systemone",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urlopen(request) as response:
    print(json.dumps(json.load(response), indent=4))
```

Send an image request with typed answers:

```python
import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen

base_url = "http://HOST_IP:8000"
image = base64.b64encode(
    Path("prompts/cats.png").read_bytes()
).decode("ascii")
payload = {
    "model": "d1-omni-2b",
    "state": None,
    "questions": {
        "cats": {
            "type": "number",
            "instructions": "How many cats are there?",
            "range": [0, 10],
            "step": 1,
        },
        "remote": {
            "type": "box",
            "instructions": "Where is the remote control on the left?",
        },
        "every_cat": {
            "type": "boxes",
            "instructions": "Every cat.",
            "max": 4,
        },
    },
    "images": [f"data:image/png;base64,{image}"],
}
request = Request(
    f"{base_url}/v1/systemone",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urlopen(request) as response:
    print(json.dumps(json.load(response), indent=2))
```
"""

import argparse
import base64
import binascii
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen

from flask import Flask, jsonify, render_template, request
from PIL import Image
import yaml

from prompt_utils import load_prompt


MODEL_ID = "LiquidAI/d1-Omni-2B"
MODEL_ALIAS = "d1-omni-2b"
MAX_REQUEST_BYTES = 64 * 1024 * 1024
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
model = None
torch = None
inference_lock = threading.Lock()


def api_error(message: str, error_type: str = "invalid_request_error"):
    return jsonify(
        {
            "error": {
                "message": message,
                "type": error_type,
            }
        }
    )


def image_from_data_url(data_url: str):
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise ValueError("Each image must be an inline image data URL.")
    try:
        metadata, encoded = data_url.split(",", 1)
    except ValueError as exc:
        raise ValueError("Image data URL is malformed.") from exc
    if ";base64" not in metadata:
        raise ValueError("Image data URL must contain base64 data.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Image data URL has invalid base64 data.") from exc
    return image_from_bytes(content)


def image_from_bytes(content: bytes):
    try:
        with Image.open(BytesIO(content)) as image:
            return image.convert("RGB")
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not decode image: {exc}") from exc


def load_example_image(prompt_path: Path, source: str):
    parsed = urlsplit(source)
    if parsed.scheme in {"http", "https"}:
        with urlopen(source, timeout=30) as response:
            content = response.read(MAX_REQUEST_BYTES + 1)
    elif parsed.scheme:
        raise ValueError("Example images must use HTTP(S) or a local path.")
    else:
        image_path = Path(source)
        if not image_path.is_absolute():
            image_path = prompt_path.parent / image_path
        content = image_path.read_bytes()

    if len(content) > MAX_REQUEST_BYTES:
        raise ValueError("Example image exceeds the 64 MiB limit.")
    return image_from_bytes(content)


def available_prompts() -> list[str]:
    return sorted(path.name for path in PROMPT_DIR.glob("*.d.yaml"))


def example_label(example: str | dict[str, str]) -> str:
    if isinstance(example, str):
        return example
    return example.get("text") or example["image"]


def render_prompt_page(
    selected_prompt: str | None = None,
    selected_example: int = 0,
    output: str | None = None,
    error: str | None = None,
    status: int = 200,
):
    prompts = available_prompts()
    if selected_prompt not in prompts:
        selected_prompt = prompts[0] if prompts else None

    examples = []
    prompt_state = None
    if selected_prompt:
        prompt = load_prompt(
            PROMPT_DIR / selected_prompt,
            allow_image_examples=True,
        )
        prompt_state = prompt["state"]
        examples = [
            {"index": index, "label": example_label(example)}
            for index, example in enumerate(prompt["examples"])
        ]

    return (
        render_template(
            "prompt_runner.html",
            prompts=prompts,
            selected_prompt=selected_prompt,
            selected_example=selected_example,
            prompt_state=prompt_state,
            examples=examples,
            output=output,
            error=error,
        ),
        status,
    )


@app.errorhandler(413)
def request_too_large(_error):
    return api_error("Request body exceeds the 64 MiB limit."), 413


@app.get("/ui")
def prompt_ui():
    selected_prompt = request.args.get("prompt")
    if selected_prompt and selected_prompt not in available_prompts():
        return render_prompt_page(
            error="Unknown prompt selection.",
            status=400,
        )
    return render_prompt_page(selected_prompt)


@app.post("/ui/run")
def run_ui_example():
    selected_prompt = request.form.get("prompt", "")
    if selected_prompt not in available_prompts():
        return render_prompt_page(
            error="Unknown prompt selection.",
            status=400,
        )
    try:
        selected_example = int(request.form.get("example", ""))
    except ValueError:
        return render_prompt_page(
            selected_prompt,
            error="Choose a valid example.",
            status=400,
        )

    try:
        prompt_path = PROMPT_DIR / selected_prompt
        prompt = load_prompt(prompt_path, allow_image_examples=True)
        examples = prompt["examples"]
        if not 0 <= selected_example < len(examples):
            return render_prompt_page(
                selected_prompt,
                error="Choose a valid example.",
                status=400,
            )
        example = examples[selected_example]

        if isinstance(example, dict):
            state = prompt["state"]
            if example.get("text"):
                state += f"\n\nImage description: {example['text']}"
            media = [load_example_image(prompt_path, example["image"])]
        else:
            state = f"{prompt['state']}\n\nUser message: {example}"
            media = None

        if model is None or torch is None:
            raise RuntimeError("The decision model is not loaded.")
        with inference_lock, torch.inference_mode():
            result = model.system_one(
                state,
                prompt["questions"],
                media=media,
            )
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        app.logger.exception("Could not run prompt example")
        return render_prompt_page(
            selected_prompt,
            error=str(exc),
            status=500,
        )

    return render_prompt_page(
        selected_prompt,
        selected_example,
        output=json.dumps(result, indent=2, ensure_ascii=False),
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None})


@app.get("/api/v1/models")
def list_models():
    return jsonify(
        {
            "models": [
                {
                    "type": "decision",
                    "loaded_instances": [{"id": MODEL_ALIAS}],
                }
            ]
        }
    )


@app.post("/v1/systemone")
def system_one():
    if model is None or torch is None:
        return (
            api_error("The decision model is not loaded.", "server_error"),
            503,
        )

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("Request body must be a JSON object."), 400
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        return api_error("'questions' must be a non-empty object."), 400
    images = payload.get("images", [])
    if not isinstance(images, list):
        return api_error("'images' must be a list."), 400

    try:
        media = [image_from_data_url(image) for image in images]
    except ValueError as exc:
        return api_error(str(exc)), 400

    try:
        with inference_lock, torch.inference_mode():
            result = model.system_one(
                payload.get("state"),
                questions,
                media=media or None,
            )
        return jsonify(result)
    except ValueError as exc:
        return api_error(str(exc)), 400
    except Exception as exc:
        app.logger.exception("D1 Omni inference failed")
        return api_error(str(exc), "server_error"), 500


def load_model(model_id: str) -> None:
    import torch as torch_module
    from transformers import AutoModel

    if not torch_module.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available. Check the NVIDIA driver and GPU setup."
        )
    dtype = (
        torch_module.bfloat16
        if torch_module.cuda.is_bf16_supported()
        else torch_module.float16
    )
    print(f"Loading {model_id} on CUDA ({dtype})...")
    loaded_model = AutoModel.from_pretrained(
        model_id,
        trust_remote_code=True,
        dtype=dtype,
    ).to("cuda")
    loaded_model.eval()

    global model, torch
    model = loaded_model
    torch = torch_module
    print("Model loaded.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default=os.environ.get("D1_HOST", "0.0.0.0"),
        help="interface to listen on",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("D1_PORT", "8000")),
        help="HTTP port",
    )
    parser.add_argument(
        "--model-id",
        default=os.environ.get("D1_MODEL_ID", MODEL_ID),
        help="Hugging Face model ID",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    load_model(args.model_id)
    print(f"Serving {args.model_id} at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Server failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
