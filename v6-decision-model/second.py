#!/usr/bin/env python3
"""Ask an LM Studio decision model once with a YAML prompt and image."""

import argparse
import base64
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

import yaml

from prompt_utils import load_prompt
from tools import make_headers, request_json

DEFAULT_MODEL = "d1-omni-2b"
DEFAULT_URL = "http://192.168.50.60:1234"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt_file", type=Path, help="YAML prompt file")
    parser.add_argument(
        "--image",
        type=Path,
        help="image file to use instead of the first YAML example image",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_URL)
    return parser.parse_args()


def read_image(source: str, base_dir: Path) -> bytes:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        with urlopen(source, timeout=30) as response:
            return response.read()
    if parsed.scheme:
        raise ValueError("Image must be a local path or an HTTP(S) URL.")

    path = Path(source)
    if not path.is_absolute():
        path = base_dir / path
    return path.read_bytes()


def image_data_url(source: str, base_dir: Path) -> str:
    image = read_image(source, base_dir)
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif image.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    elif image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        mime_type = "image/webp"
    else:
        raise ValueError("Image must be a JPEG, PNG, or WebP file.")

    encoded = base64.b64encode(image).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def ask_with_image(
    prompt: dict[str, Any],
    image_source: str,
    image_base_dir: Path,
    image_text: str,
    model_id: str,
    base_url: str,
    headers: dict[str, str],
) -> Any:
    state = prompt["state"]
    if image_text:
        state = f"{state}\n\nImage description: {image_text}"
    payload = {
        "model": model_id,
        "state": state,
        "questions": prompt["questions"],
        "images": [image_data_url(image_source, image_base_dir)],
    }
    return request_json(
        f"{base_url.rstrip('/')}/v1/systemone",
        headers,
        payload,
    )


def main() -> None:
    args = parse_args()
    try:
        prompt = load_prompt(
            args.prompt_file,
            allow_image_examples=True,
        )
        examples = prompt["examples"]
        example = examples[0] if examples else {}
        if isinstance(example, dict):
            image_text = example.get("text", "")
            example_image = example.get("image", "")
        else:
            image_text = example
            example_image = ""
        image_source = str(args.image or example_image)
        if not image_source:
            raise ValueError(
                "Provide --image or define an image in the first example."
            )
        image_base_dir = (
            Path.cwd() if args.image else args.prompt_file.parent
        )
        result = ask_with_image(
            prompt,
            image_source,
            image_base_dir,
            image_text,
            args.model,
            args.base_url,
            make_headers(),
        )
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(yaml.safe_dump(result, sort_keys=False, indent=4), end="")


if __name__ == "__main__":
    main()
