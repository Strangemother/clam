import pathlib
import markdown
from flask import Flask, render_template, jsonify

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
        # Strip all extensions (e.g. init.prompt.md → init)
        label = f.name
        for _ in f.suffixes:
            label = pathlib.Path(label).stem
        # Prefix with parent folder(s) when nested (e.g. self / init)
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
