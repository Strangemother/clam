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
import os
import platform
from pathlib import Path
import re
import sys
import tempfile
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
)
from PIL import Image
import yaml

from prompt_utils import load_prompt, parse_prompt
from tools import (
    list_loaded_decision_models,
    make_headers,
    request_json,
)


MODEL_ID = "LiquidAI/d1-Omni-2B"
MODEL_ALIAS = "d1-omni-2b"
DEFAULT_LM_STUDIO_URL = "http://192.168.50.60:1234"
LM_STUDIO_QUESTION_TYPES = {"noul", "choice", "score"}
MAX_REQUEST_BYTES = 64 * 1024 * 1024
PROMPT_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\.d\.yaml\Z")
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
app.config["LM_STUDIO_BASE_URL"] = os.environ.get(
    "LM_STUDIO_BASE_URL",
    DEFAULT_LM_STUDIO_URL,
).rstrip("/")
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


def append_state_text(state: str, text: str) -> str:
    return f"{state}\n\n{text}" if state else text


def prompt_details(prompt_name: str, source: str) -> dict:
    prompt = parse_prompt(source, allow_image_examples=True)
    return {
        "name": prompt_name,
        "yaml": source,
        "state": prompt["state"],
        "questions": prompt["questions"],
        "examples": [
            {
                "index": index,
                "label": example_label(example),
                "is_image": isinstance(example, dict),
            }
            for index, example in enumerate(prompt["examples"])
        ],
        "lm_studio_questions_supported": all(
            question.get("type") in LM_STUDIO_QUESTION_TYPES
            for question in prompt["questions"].values()
        ),
    }


def valid_prompt_filename(prompt_name: str) -> bool:
    return PROMPT_FILENAME.fullmatch(prompt_name) is not None


def save_prompt_source(
    prompt_path: Path,
    source: str,
    create_new: bool,
) -> None:
    if create_new:
        created = False
        try:
            with prompt_path.open("x", encoding="utf-8") as prompt_file:
                created = True
                prompt_file.write(source)
        except OSError:
            if created:
                prompt_path.unlink(missing_ok=True)
            raise
        return

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=PROMPT_DIR,
            prefix=".prompt-",
            suffix=".tmp",
            delete=False,
        ) as prompt_file:
            temporary_path = Path(prompt_file.name)
            prompt_file.write(source)
            prompt_file.flush()
            os.fsync(prompt_file.fileno())
        os.replace(temporary_path, prompt_path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


@app.errorhandler(413)
def request_too_large(_error):
    return api_error("Request body exceeds the 64 MiB limit."), 413


@app.get("/ui")
def prompt_ui():
    return render_template(
        "prompt_runner.html",
        config={
            "prompts": available_prompts(),
            "model_alias": MODEL_ALIAS,
            "lm_studio_base_url": app.config["LM_STUDIO_BASE_URL"],
            "api_base_url": request.host_url.rstrip("/"),
            "prompt_url": (
                url_for(
                    "ui_prompt_details",
                    prompt_name="prompt-placeholder",
                ).rsplit("/", 1)[0]
                + "/"
            ),
            "image_url": (
                url_for(
                    "ui_prompt_image",
                    prompt_name="prompt-placeholder",
                    example_index=0,
                ).rsplit("/", 2)[0]
            ),
            "prompt_collection_url": url_for("ui_create_prompt"),
            "prompt_save_url": (
                url_for(
                    "ui_update_prompt",
                    prompt_name="prompt-placeholder",
                ).rsplit("/", 1)[0]
                + "/"
            ),
            "models_url": url_for("ui_lm_studio_models"),
            "run_url": url_for("run_ui_example"),
        },
    )


@app.get("/ui/api/prompts/<path:prompt_name>")
def ui_prompt_details(prompt_name: str):
    if prompt_name not in available_prompts():
        return api_error("Unknown prompt selection."), 404

    prompt_path = PROMPT_DIR / prompt_name
    try:
        source = prompt_path.read_text(encoding="utf-8")
        details = prompt_details(prompt_name, source)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return api_error(f"Could not load prompt: {exc}"), 400

    return jsonify(details)


def save_prompt_request(
    source: object,
    prompt_name: object,
    create_new: bool,
):
    if not isinstance(prompt_name, str) or not valid_prompt_filename(
        prompt_name
    ):
        return api_error(
            "Prompt filename must use letters, numbers, hyphens, or "
            "underscores and end in '.d.yaml'."
        ), 400
    if not isinstance(source, str):
        return api_error("Prompt YAML must be a string."), 400

    try:
        details = prompt_details(prompt_name, source)
    except (ValueError, yaml.YAMLError) as exc:
        return api_error(f"Invalid prompt YAML: {exc}"), 400

    prompt_path = PROMPT_DIR / prompt_name
    if not create_new and prompt_name not in available_prompts():
        return api_error("The prompt to overwrite does not exist."), 404

    try:
        save_prompt_source(prompt_path, source, create_new)
    except FileExistsError:
        return api_error(
            "A prompt with that filename already exists. "
            "Choose another name to avoid overwriting it."
        ), 409
    except OSError as exc:
        app.logger.exception("Could not save prompt %s", prompt_name)
        return api_error(
            f"Could not save prompt: {exc}",
            "server_error",
        ), 500

    return jsonify(details)


@app.post("/ui/api/prompts")
def ui_create_prompt():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("Request body must be a JSON object."), 400
    return save_prompt_request(
        payload.get("yaml"),
        payload.get("name"),
        create_new=True,
    )


@app.put("/ui/api/prompts/<path:prompt_name>")
def ui_update_prompt(prompt_name: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("Request body must be a JSON object."), 400
    return save_prompt_request(
        payload.get("yaml"),
        prompt_name,
        create_new=False,
    )


@app.get(
    "/ui/api/prompt-images/<string:prompt_name>/<int:example_index>"
)
def ui_prompt_image(prompt_name: str, example_index: int):
    if prompt_name not in available_prompts():
        return api_error("Unknown prompt selection."), 404

    prompt_path = PROMPT_DIR / prompt_name
    try:
        prompt = load_prompt(prompt_path, allow_image_examples=True)
        examples = prompt["examples"]
        if not 0 <= example_index < len(examples):
            return api_error("Choose a valid image example."), 404

        example = examples[example_index]
        if not isinstance(example, dict):
            return api_error("The selected example is not an image."), 400

        image = load_example_image(prompt_path, example["image"])
        image_buffer = BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return api_error(f"Could not load prompt image: {exc}"), 400

    return send_file(image_buffer, mimetype="image/png", max_age=0)


@app.get("/ui/lm-studio/models")
def ui_lm_studio_models():
    try:
        model_ids = list_loaded_decision_models(
            app.config["LM_STUDIO_BASE_URL"],
            make_headers(),
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"models": model_ids})


@app.post("/ui/run")
def run_ui_example():
    selected_prompt = request.form.get("prompt", "")
    selected_backend = request.form.get("backend", "")
    selected_model = request.form.get("model", "")
    user_prompt = request.form.get("user_prompt", "").strip()
    if selected_prompt not in available_prompts():
        return api_error("Select a valid prompt file."), 400
    if selected_backend not in {"local", "lm_studio"}:
        return api_error("Select a model backend."), 400

    raw_example = request.form.get("example", "").strip()
    try:
        selected_example = int(raw_example) if raw_example else None
    except ValueError:
        return api_error("Choose a valid example."), 400

    try:
        prompt_path = PROMPT_DIR / selected_prompt
        prompt = load_prompt(prompt_path, allow_image_examples=True)
        examples = prompt["examples"]
        selected_example_data = (
            examples[selected_example]
            if selected_example is not None
            and 0 <= selected_example < len(examples)
            else None
        )
        if selected_example is not None and selected_example_data is None:
            return api_error("Choose a valid example."), 400
        if not user_prompt and selected_example_data is None:
            return api_error(
                "Enter a user message or select an example."
            ), 400

        user_state = request.form.get("prompt_state", prompt["state"])
        image_override = request.files.get("image_override")
        has_image_override = bool(
            image_override and image_override.filename
        )
        if has_image_override and not isinstance(
            selected_example_data, dict
        ):
            return api_error(
                "Select an image example before uploading an override."
            ), 400

        if selected_backend == "lm_studio":
            if not selected_model:
                return api_error(
                    "Select a loaded LM Studio decision model."
                ), 400
            if has_image_override:
                return api_error(
                    "LM Studio mode does not support image inputs."
                ), 400
            if (
                isinstance(selected_example_data, dict)
                and not user_prompt
            ):
                return api_error(
                    "LM Studio mode does not support image examples. "
                    "Enter a text message to use instead."
                ), 400
            unsupported_questions = [
                f"{name} ({question.get('type', 'unknown')})"
                for name, question in prompt["questions"].items()
                if question.get("type") not in LM_STUDIO_QUESTION_TYPES
            ]
            if unsupported_questions:
                return api_error(
                    "LM Studio supports only noul, choice, and score "
                    "questions. Unsupported: "
                    + ", ".join(unsupported_questions)
                ), 400
            if isinstance(selected_example_data, dict):
                example_text = user_prompt
            elif user_prompt:
                example_text = user_prompt
            else:
                example_text = selected_example_data or ""
            state = append_state_text(
                user_state,
                f"User message: {example_text}" if example_text else "",
            )
            result = request_json(
                f"{app.config['LM_STUDIO_BASE_URL']}/v1/systemone",
                make_headers(),
                {
                    "model": selected_model,
                    "state": state,
                    "questions": prompt["questions"],
                },
            )
        else:
            if isinstance(selected_example_data, dict):
                example = selected_example_data
                state = user_state
                if example.get("text"):
                    state = append_state_text(
                        state,
                        f"Image description: {example['text']}",
                    )
                if user_prompt:
                    state = append_state_text(
                        state,
                        f"User message: {user_prompt}",
                    )
                if has_image_override:
                    image_bytes = image_override.stream.read(
                        MAX_REQUEST_BYTES + 1
                    )
                    if len(image_bytes) > MAX_REQUEST_BYTES:
                        raise ValueError(
                            "Image override exceeds the 64 MiB limit."
                        )
                    media = [image_from_bytes(image_bytes)]
                else:
                    media = [
                        load_example_image(
                            prompt_path,
                            example["image"],
                        )
                    ]
            else:
                example = user_prompt or selected_example_data or ""
                state = append_state_text(
                    user_state,
                    f"User message: {example}" if example else "",
                )
                media = None

            if model is None or torch is None:
                return api_error(
                    "The decision model is not loaded.",
                    "server_error",
                ), 503
            with inference_lock, torch.inference_mode():
                result = model.system_one(
                    state,
                    prompt["questions"],
                    media=media,
                )
    except ValueError as exc:
        return api_error(str(exc)), 400
    except (OSError, RuntimeError, yaml.YAMLError) as exc:
        if selected_backend == "lm_studio":
            app.logger.exception("LM Studio request failed")
            return api_error(str(exc), "server_error"), 502
        app.logger.exception("Could not run prompt example")
        return api_error(str(exc), "server_error"), 500

    return jsonify(result)


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
    )
    configure_windows_attention()
    loaded_model = loaded_model.to("cuda")
    loaded_model.eval()

    global model, torch
    model = loaded_model
    torch = torch_module
    print("Model loaded.")


def disable_fused_attention(query) -> bool:
    del query
    return False


def configure_windows_attention() -> None:
    if platform.system() != "Windows":
        return

    attention_modules = [
        module
        for module in tuple(sys.modules.values())
        if module is not None
        and getattr(module, "d1_attention", None) is not None
        and getattr(module, "_fused", None) is not None
    ]
    if not attention_modules:
        raise RuntimeError(
            "Could not find D1 Omni's attention module for the "
            "Windows SDPA fallback."
        )

    for module in attention_modules:
        module._fused = disable_fused_attention
    print("Using PyTorch SDPA instead of fused FlashAttention on Windows.")


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
        default=int(os.environ.get("D1_PORT", "8430")),
        help="HTTP port",
    )
    parser.add_argument(
        "--model-id",
        default=os.environ.get("D1_MODEL_ID", MODEL_ID),
        help="Hugging Face model ID",
    )
    parser.add_argument(
        "--lm-studio-url",
        default=os.environ.get(
            "LM_STUDIO_BASE_URL",
            DEFAULT_LM_STUDIO_URL,
        ),
        help="LM Studio API base URL used by the browser UI",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    parsed_lm_studio_url = urlsplit(args.lm_studio_url)
    if (
        parsed_lm_studio_url.scheme not in {"http", "https"}
        or not parsed_lm_studio_url.netloc
    ):
        raise ValueError("LM Studio URL must be an HTTP(S) URL.")
    app.config["LM_STUDIO_BASE_URL"] = args.lm_studio_url.rstrip("/")
    load_model(args.model_id)
    print(f"Serving {args.model_id} at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Server failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
