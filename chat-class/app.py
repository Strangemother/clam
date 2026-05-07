import pathlib
import markdown
from jinja2 import Template, TemplateSyntaxError
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Fully-qualified path to your prompts directory.
# Change this to point at any folder of .md / .txt prompt files.
fp = 'C:/Users/jay/Documents/projects/olloma-quick/v5_2/prompts/'
PROMPTS_DIR = pathlib.Path(fp)


@app.route('/')
def index():
    return render_template('index-vue.html')


@app.route('/prompts/')
def list_prompts():
    """Return a JSON list of prompt files found recursively under PROMPTS_DIR.

    Each entry has:
      name  — filename without extension, used as a display label
      path  — path relative to PROMPTS_DIR, used as a unique key
    """
    files = sorted(PROMPTS_DIR.rglob('*.md')) + sorted(PROMPTS_DIR.rglob('*.txt'))
    prompts = []
    for f in files:
        if not f.is_file():
            continue
        rel  = f.relative_to(PROMPTS_DIR)
        # Strip only the trailing file-type suffixes (.prompt.md, .md, .txt)
        # so that version dots like .v2 are preserved.
        label = f.name
        for ext in ('.prompt.md', '.prompt.txt', '.md', '.txt'):
            if label.lower().endswith(ext):
                label = label[: len(label) - len(ext)]
                break
        # Prefix with parent folder(s) when nested (e.g. self / example.v2)
        if len(rel.parts) > 1:
            label = ' / '.join(list(rel.parts[:-1]) + [label])
        prompts.append({'name': label, 'path': str(rel)})

    return jsonify(prompts)


@app.route('/prompts/<path:prompt_path>')
def get_prompt(prompt_path):
    """Return parsed prompt data as JSON.

    Keys:
      content     — prompt text with metadata header stripped (use as system prompt)
      description — value of the 'description' meta key, or ''
      title       — value of the 'title' meta key, or filename stem
      model       — first value of 'model'/'models' meta key, or ''
      meta        — all raw meta key/value pairs
    """
    target = (PROMPTS_DIR / prompt_path).resolve()

    # Guard: ensure the resolved path is still inside PROMPTS_DIR
    if not str(target).startswith(str(PROMPTS_DIR.resolve())):
        return jsonify({'error': 'invalid path'}), 400

    if not target.exists():
        return jsonify({'error': 'not found'}), 404

    raw = target.read_text(encoding='utf-8', errors='replace')
    md  = markdown.Markdown(extensions=['meta'])
    md.convert(raw)
    # md.lines is the text after the meta preprocessor has stripped the header block
    content = '\n'.join(md.lines).strip()
    meta    = {k: v for k, v in md.Meta.items()}

    def first(key, default=''):
        vals = meta.get(key) or []
        return vals[0] if vals else default

    # Derive display name from filename (strip all suffixes)
    stem = target.name
    for _ in target.suffixes:
        stem = pathlib.Path(stem).stem

    return jsonify({
        'content':     content,
        'description': first('description'),
        'title':       first('title', stem),
        'model':       first('models') or first('model'),
        'meta':        meta,
    })


@app.route('/prompts/render', methods=['POST'])
def render_prompt():
    """Render a Jinja2 prompt template with provided variables.

    POST body (JSON):
      template  — raw Jinja2 template string   (required unless 'path' given)
      path      — path relative to PROMPTS_DIR (alternative to 'template';
                  uses the stripped content from the prompt file)
      vars      — dict of variables to inject  (optional, defaults to {})

    Standard vars always injected (can be overridden by 'vars'):
      timestamp — current UTC ISO-8601 string

    Returns JSON:
      { rendered: "...", error: null }
      or on failure:
      { rendered: null, error: "message" }
    """
    body = request.get_json(silent=True) or {}

    template_str = body.get('template')
    prompt_path  = body.get('path')
    variables    = dict(body.get('vars') or {})

    # Inject standard variables (user may override)
    from datetime import datetime, timezone
    variables.setdefault('timestamp', datetime.now(timezone.utc).isoformat())

    # Load template string from file if path given
    if not template_str and prompt_path:
        target = (PROMPTS_DIR / prompt_path).resolve()
        if not str(target).startswith(str(PROMPTS_DIR.resolve())):
            return jsonify({'rendered': None, 'error': 'invalid path'}), 400
        if not target.exists():
            return jsonify({'rendered': None, 'error': 'not found'}), 404
        raw = target.read_text(encoding='utf-8', errors='replace')
        md  = markdown.Markdown(extensions=['meta'])
        md.convert(raw)
        template_str = '\n'.join(md.lines).strip()

    if not template_str:
        return jsonify({'rendered': None, 'error': 'no template provided'}), 400

    try:
        rendered = Template(template_str).render(**variables)
    except TemplateSyntaxError as e:
        return jsonify({'rendered': None, 'error': f'template error: {e}'}), 422

    return jsonify({'rendered': rendered, 'error': None})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
