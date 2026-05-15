goal:

A simple UI to read and write text to the vector DB. The result should be a simple UI that allows users to input text.
A user can "embed" or "request". On "embed", the text will be embedded and stored in the vector DB. 
On "request", the result will be the most similar text in the vector DB - as actual text, not the embedding vector.

The result text will be stored vector knowledge, and can be given in a prompt as additional context to the LLM.

Using the SQLite AI. Python version

- Tool: https://github.com/sqliteai/sqlite-ai
- Python: https://github.com/sqliteai/sqlite-ai/blob/main/packages/python/README.md
- API: https://github.com/sqliteai/sqlite-ai/blob/main/API.md

Build:

1. A flask UI
2. one page
3. the sqlite AI.

Minimal dependencies.

## Minimal PoC

Files:

- `app.py` - minimal Flask bootstrap only
- `routes.py` - Flask endpoints and request handling
- `embed_tool.py` - SQLite-AI loading, storage, and similarity lookup
- `flask_assets/templates/index.html` - page template
- `flask_assets/static/app.css` - page styles
- `requirements.txt` - minimal install list

Run:

```bash
cd /workspaces/clam/text-embed-tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Notes:

- Set `MODEL_PATH` near the top of `app.py`.
- SQLite-AI is loaded as a SQLite extension in Python; this PoC exposes simple Flask endpoints around it.
- The server binds to `0.0.0.0`, so you can hit it from another machine.
- Flask files live under `flask_assets/`; stored data goes into `embed_tool_assets/knowledge.db`.

Quick JSON test:

```bash
curl -X POST http://YOUR_HOST:5000/embed \
	-H 'Content-Type: application/json' \
	-d '{"text":"Cats like warm windows."}'

curl -X POST http://YOUR_HOST:5000/request \
	-H 'Content-Type: application/json' \
	-d '{"text":"Tell me about cats."}'
```

