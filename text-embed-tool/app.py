from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from embed_tool import EmbeddingStore


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBED_TOOL_ASSETS_DIR = os.path.join(BASE_DIR, "embed_tool_assets")

DB_PATH = os.path.join(EMBED_TOOL_ASSETS_DIR, "knowledge.db")
MODEL_PATH = "C:/Users/jay/.lmstudio/models/jinaai/jina-embeddings-v5-text-small-retrieval/v5-small-retrieval-Q8_0.gguf"
SQLITE_AI_PACKAGE = "sqliteai.binaries.cpu"
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

app = Flask(__name__)

try:
    STORE = EmbeddingStore(DB_PATH, MODEL_PATH, SQLITE_AI_PACKAGE)
    STARTUP_ERROR = None
except Exception as exc:  # pragma: no cover - startup guard for missing local deps
    STORE = None
    STARTUP_ERROR = str(exc)


def handle_action(text: str, action: str) -> tuple[dict[str, object] | None, str | None, int]:
    if not text:
        return None, "text is required", 400
    if STORE is None:
        return None, STARTUP_ERROR or "SQLite-AI failed to start.", 500

    try:
        if action == "embed":
            entry_id = STORE.add(text)
            return {"action": "embed", "stored": True, "id": entry_id, "text": text}, None, 200
        if action in {"retrieve", "request"}:
            match = STORE.find_best_match(text)
            return {"action": "retrieve", "query": text, "match": match}, None, 200
        return None, "action must be embed or retrieve", 400
    except Exception as exc:
        return None, str(exc), 500

@app.route("/", methods=["GET", "POST"])
def index():
    text = ""
    action = "embed"
    result = None
    error = None

    if request.method == "POST":
        payload = request.get_json(silent=True) or {} if request.is_json else request.form
        text = str(payload.get("text", "")).strip()
        action = str(payload.get("action", "embed")).strip().lower()
        result, error, status = handle_action(text, action)

        if request.is_json or request.headers.get("Accept", "").startswith("application/json"):
            body = result if error is None else {"error": error}
            return jsonify(body), status

    return render_template(
        "index.html",
        startup_error=STARTUP_ERROR,
        text=text,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)