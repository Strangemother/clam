"""
prompting.py
────────────────────────────────────────────────────────────────────────────
Flask Blueprint for the /prompting sub-app.

Registers:
  GET  /prompting/               → serves prompting.html
  GET  /prompting/prompts/       → lists prompt files as JSON
  GET  /prompting/prompts/<path> → returns parsed prompt content/meta
  POST /prompting/prompts/render → renders a Jinja2 prompt template

PROMPTS_DIR defaults to v5_2/prompts/ relative to this file's parent,
but can be overridden with the PROMPTS_DIR environment variable.
"""

import os
import pathlib
import markdown
from datetime import datetime, timezone

from jinja2 import Template, TemplateSyntaxError
from flask import Blueprint, render_template, jsonify, request

# ── prompts directory ────────────────────────────────────────────────────────

_DEFAULT_PROMPTS = pathlib.Path(__file__).parent.parent / 'v5_2' / 'prompts'
PROMPTS_DIR = pathlib.Path(os.environ.get('PROMPTS_DIR', str(_DEFAULT_PROMPTS)))

# ── Blueprint ────────────────────────────────────────────────────────────────

prompting_bp = Blueprint('prompting', __name__, url_prefix='/prompting')


# ── helpers ──────────────────────────────────────────────────────────────────

def _list_prompt_files():
    """Return a list of {name, path} dicts for every .md/.txt under PROMPTS_DIR."""
    if not PROMPTS_DIR.exists():
        return []
    files = sorted(PROMPTS_DIR.rglob('*.md')) + sorted(PROMPTS_DIR.rglob('*.txt'))
    prompts = []
    for f in files:
        if not f.is_file():
            continue
        rel   = f.relative_to(PROMPTS_DIR)
        label = f.name
        for ext in ('.prompt.md', '.prompt.txt', '.md', '.txt'):
            if label.lower().endswith(ext):
                label = label[: len(label) - len(ext)]
                break
        if len(rel.parts) > 1:
            label = ' / '.join(list(rel.parts[:-1]) + [label])
        prompts.append({'name': label, 'path': str(rel)})
    return prompts


def _parse_prompt_file(target: pathlib.Path) -> dict:
    """Parse a .md prompt file, strip meta header, return content + metadata."""
    raw = target.read_text(encoding='utf-8', errors='replace')
    md  = markdown.Markdown(extensions=['meta'])
    md.convert(raw)
    content = '\n'.join(md.lines).strip()
    meta    = {k: v for k, v in md.Meta.items()}

    def first(key, default=''):
        vals = meta.get(key) or []
        return vals[0] if vals else default

    stem = target.name
    for _ in target.suffixes:
        stem = pathlib.Path(stem).stem

    return {
        'content':     content,
        'description': first('description'),
        'title':       first('title', stem),
        'model':       first('models') or first('model'),
        'meta':        meta,
    }


def _safe_target(prompt_path: str):
    """Resolve prompt_path inside PROMPTS_DIR; return (target, error_response)."""
    target = (PROMPTS_DIR / prompt_path).resolve()
    if not str(target).startswith(str(PROMPTS_DIR.resolve())):
        return None, (jsonify({'error': 'invalid path'}), 400)
    if not target.exists():
        return None, (jsonify({'error': 'not found'}), 404)
    return target, None


# ── routes ───────────────────────────────────────────────────────────────────

@prompting_bp.route('/', strict_slashes=False)
def index():
    return render_template('prompting.html')


@prompting_bp.route('/prompts/', strict_slashes=False)
def list_prompts():
    """Return JSON list of all prompt files under PROMPTS_DIR."""
    return jsonify(_list_prompt_files())


@prompting_bp.route('/prompts/<path:prompt_path>')
def get_prompt(prompt_path):
    """Return parsed prompt data as JSON (content, title, description, model, meta)."""
    target, err = _safe_target(prompt_path)
    if err:
        return err
    return jsonify(_parse_prompt_file(target))


@prompting_bp.route('/prompts/render', methods=['POST'])
def render_prompt():
    """Render a Jinja2 prompt template with provided variables.

    POST body (JSON):
      template  — raw template string  (required unless 'path' given)
      path      — prompt file path     (alternative to 'template')
      vars      — dict of variables    (optional)

    Always injects:  timestamp (UTC ISO-8601)

    Returns: { rendered: str, error: null }  or  { rendered: null, error: str }
    """
    body         = request.get_json(silent=True) or {}
    template_str = body.get('template')
    prompt_path  = body.get('path')
    variables    = dict(body.get('vars') or {})
    variables.setdefault('timestamp', datetime.now(timezone.utc).isoformat())

    if not template_str and prompt_path:
        target, err = _safe_target(prompt_path)
        if err:
            return err
        template_str = _parse_prompt_file(target)['content']

    if not template_str:
        return jsonify({'rendered': None, 'error': 'no template provided'}), 400

    try:
        rendered = Template(template_str).render(**variables)
    except TemplateSyntaxError as e:
        return jsonify({'rendered': None, 'error': f'template error: {e}'}), 422

    return jsonify({'rendered': rendered, 'error': None})
