"""Prompt, layout, and template-rendering routes for the prompting app."""

import json
import os
import pathlib
from datetime import datetime, timezone

import markdown
from flask import jsonify, render_template, request
from jinja2 import Template, TemplateSyntaxError

from prompting_core import prompting_bp


_DEFAULT_PROMPTS = pathlib.Path(__file__).parent.parent / "v5_2" / "prompts"
PROMPTS_DIR = pathlib.Path(
    os.environ.get("PROMPTS_DIR", str(_DEFAULT_PROMPTS))
)


def _list_prompt_files():
    """Return prompt file entries under PROMPTS_DIR."""
    if not PROMPTS_DIR.exists():
        return []

    files = (
        sorted(PROMPTS_DIR.rglob("*.md"))
        + sorted(PROMPTS_DIR.rglob("*.txt"))
    )
    prompts = []

    for file_path in files:
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(PROMPTS_DIR)
        label = file_path.name
        for extension in (".prompt.md", ".prompt.txt", ".md", ".txt"):
            if label.lower().endswith(extension):
                label = label[: len(label) - len(extension)]
                break

        if len(relative_path.parts) > 1:
            label = " / ".join([*relative_path.parts[:-1], label])

        prompts.append({"name": label, "path": str(relative_path)})

    return prompts


def _parse_prompt_file(target):
    """Parse a prompt file and return its content plus markdown metadata."""
    raw = target.read_text(encoding="utf-8", errors="replace")
    md = markdown.Markdown(extensions=["meta"])
    md.convert(raw)
    content = "\n".join(md.lines).strip()
    meta = {key: value for key, value in md.Meta.items()}

    def first(key, default=""):
        values = meta.get(key) or []
        return values[0] if values else default

    stem = target.name
    for _ in target.suffixes:
        stem = pathlib.Path(stem).stem

    return {
        "content": content,
        "description": first("description"),
        "title": first("title", stem),
        "model": first("models") or first("model"),
        "meta": meta,
    }


def _safe_target(prompt_path):
    """Resolve prompt_path inside PROMPTS_DIR."""
    target = (PROMPTS_DIR / prompt_path).resolve()
    if not str(target).startswith(str(PROMPTS_DIR.resolve())):
        return None, (jsonify({"error": "invalid path"}), 400)
    if not target.exists():
        return None, (jsonify({"error": "not found"}), 404)
    return target, None


def _safe_layout_target(layout_name):
    """Resolve a readable layout JSON file inside PROMPTS_DIR."""
    raw_name = (layout_name or "").strip()
    if not raw_name:
        return None, (jsonify({"error": "no layout specified"}), 400)

    layout_path = (
        raw_name if raw_name.lower().endswith(".json") else f"{raw_name}.json"
    )
    root = PROMPTS_DIR.resolve()
    target = (PROMPTS_DIR / layout_path).resolve()

    if str(target).startswith(str(root)) and target.is_file():
        return target, None

    if "/" not in raw_name and "\\" not in raw_name:
        basename = pathlib.Path(layout_path).name
        matches = []

        for candidate in PROMPTS_DIR.rglob(basename):
            resolved = candidate.resolve()
            if not str(resolved).startswith(str(root)):
                continue
            if resolved.is_file() and resolved not in matches:
                matches.append(resolved)

        if len(matches) == 1:
            return matches[0], None

        if len(matches) > 1:
            return None, (
                jsonify(
                    {
                        "error": "ambiguous layout name",
                        "matches": [
                            str(path.relative_to(root)) for path in matches
                        ],
                    }
                ),
                409,
            )

    return None, (jsonify({"error": "layout not found"}), 404)


def _safe_layout_write_target(layout_name):
    """Resolve a writable layout JSON path inside PROMPTS_DIR."""
    raw_name = (layout_name or "").strip()
    if not raw_name:
        return None, (jsonify({"error": "no layout specified"}), 400)

    layout_path = (
        raw_name if raw_name.lower().endswith(".json") else f"{raw_name}.json"
    )
    target = (PROMPTS_DIR / layout_path).resolve()
    root = PROMPTS_DIR.resolve()

    if not str(target).startswith(str(root)):
        return None, (jsonify({"error": "invalid path"}), 400)

    return target, None


@prompting_bp.route("/", strict_slashes=False)
def index():
    """Serve the prompting canvas UI."""
    return render_template("prompting.html")


@prompting_bp.route("/layouts/<path:layout_name>", strict_slashes=False)
def get_layout(layout_name):
    """Return a prompting layout JSON file from PROMPTS_DIR."""
    target, err = _safe_layout_target(layout_name)
    if err:
        return err

    return target.read_text(encoding="utf-8", errors="replace"), 200, {
        "Content-Type": "application/json"
    }


@prompting_bp.route(
    "/layouts/<path:layout_name>", strict_slashes=False, methods=["POST"]
)
def save_layout(layout_name):
    """Save a prompting layout JSON file inside PROMPTS_DIR."""
    target, err = _safe_layout_write_target(layout_name)
    if err:
        return err

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid json payload"}), 400

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return jsonify(
        {
            "ok": True,
            "path": str(target.relative_to(PROMPTS_DIR.resolve())),
        }
    )


@prompting_bp.route("/prompts/", strict_slashes=False)
def list_prompts():
    """Return all prompt files under PROMPTS_DIR."""
    return jsonify(_list_prompt_files())


@prompting_bp.route("/prompts/<path:prompt_path>")
def get_prompt(prompt_path):
    """Return parsed prompt data as JSON."""
    target, err = _safe_target(prompt_path)
    if err:
        return err

    return jsonify(_parse_prompt_file(target))


@prompting_bp.route("/prompts/render", methods=["POST"])
def render_prompt():
    """Render a Jinja2 prompt template with the provided variables."""
    body = request.get_json(silent=True) or {}
    template_str = body.get("template")
    prompt_path = body.get("path")
    variables = dict(body.get("vars") or {})
    variables.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    if not template_str and prompt_path:
        target, err = _safe_target(prompt_path)
        if err:
            return err
        template_str = _parse_prompt_file(target)["content"]

    if not template_str:
        return (
            jsonify({"rendered": None, "error": "no template provided"}),
            400,
        )

    try:
        rendered = Template(template_str).render(**variables)
    except TemplateSyntaxError as exc:
        return (
            jsonify({"rendered": None, "error": f"template error: {exc}"}),
            422,
        )

    return jsonify({"rendered": rendered, "error": None})
