import pathlib
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Fully-qualified path to your prompts directory.
# Change this to point at any folder of .md / .txt prompt files.
PROMPTS_DIR = pathlib.Path('/workspaces/clam/v5_2/prompts')


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
    """Return the raw text content of a single prompt file."""
    target = (PROMPTS_DIR / prompt_path).resolve()

    # Guard: ensure the resolved path is still inside PROMPTS_DIR
    if not target.is_relative_to(PROMPTS_DIR.resolve()):
        return jsonify({'error': 'invalid path'}), 400

    if not target.exists():
        return jsonify({'error': 'not found'}), 404

    return target.read_text(), 200, {'Content-Type': 'text/plain; charset=utf-8'}


if __name__ == '__main__':
    app.run(debug=True, port=5000)
