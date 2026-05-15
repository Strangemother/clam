from __future__ import annotations

import importlib.resources
import json
import math
import os
import sqlite3
import threading

from flask import Flask, jsonify, render_template_string, request


BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.environ.get("TEXT_EMBED_DB", os.path.join(BASE_DIR, "knowledge.db"))
MODEL_PATH = os.environ.get("SQLITE_AI_MODEL_PATH", "")
SQLITE_AI_PACKAGE = os.environ.get("SQLITE_AI_PACKAGE", "sqliteai.binaries.cpu")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

PAGE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Text Embed PoC</title>
    <style>
      body { font-family: sans-serif; margin: 40px auto; max-width: 820px; padding: 0 16px; }
      section { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 16px 0; }
      textarea { width: 100%; min-height: 120px; }
      button { margin-top: 8px; padding: 8px 14px; }
      pre { white-space: pre-wrap; word-break: break-word; background: #f6f6f6; padding: 12px; border-radius: 6px; }
      .error { color: #8b0000; }
    </style>
  </head>
  <body>
    <h1>Text Embed PoC</h1>
    <p>Stores text plus SQLite-AI embeddings. Request returns the closest saved text.</p>

    {% if startup_error %}
      <pre class="error">{{ startup_error }}</pre>
    {% endif %}

    {% if message %}
      <pre>{{ message }}</pre>
    {% endif %}

    {% if result %}
      <pre>{{ result }}</pre>
    {% endif %}

    {% if error %}
      <pre class="error">{{ error }}</pre>
    {% endif %}

    <section>
      <h2>Embed</h2>
      <form method="post" action="/embed">
        <textarea name="text" required>{{ embed_text }}</textarea>
        <button type="submit">Embed</button>
      </form>
    </section>

    <section>
      <h2>Request</h2>
      <form method="post" action="/request">
        <textarea name="text" required>{{ request_text }}</textarea>
        <button type="submit">Request</button>
      </form>
    </section>
  </body>
</html>
"""


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def parse_embedding(raw_value: str) -> list[float]:
    data = json.loads(raw_value)

    if isinstance(data, list):
        return [float(value) for value in data]

    if isinstance(data, dict):
        if isinstance(data.get("embedding"), list):
            return [float(value) for value in data["embedding"]]
        if isinstance(data.get("embeddings"), list):
            return [float(value) for value in data["embeddings"]]
        if isinstance(data.get("data"), list) and data["data"]:
            first_item = data["data"][0]
            if isinstance(first_item, dict) and isinstance(first_item.get("embedding"), list):
                return [float(value) for value in first_item["embedding"]]

    raise ValueError(f"Unexpected embedding payload: {raw_value[:120]}")


def request_text() -> str:
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        return str(payload.get("text", "")).strip()
    return request.form.get("text", "").strip()


def wants_json() -> bool:
    return request.is_json or request.headers.get("Accept", "").startswith("application/json")


def page_response(**values):
    return render_template_string(
        PAGE,
        startup_error=STARTUP_ERROR,
        embed_text="",
        request_text="",
        message=None,
        result=None,
        error=None,
        **values,
    )


class EmbeddingStore:
    def __init__(self, db_path: str, model_path: str, sqlite_ai_package: str):
        self.db_path = db_path
        self.model_path = model_path
        self.sqlite_ai_package = sqlite_ai_package
        self.lock = threading.Lock()
        self.connection = self._connect()
        self.model_loaded = False
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row

        extension_path = importlib.resources.files(self.sqlite_ai_package) / "ai"
        connection.enable_load_extension(True)
        connection.load_extension(str(extension_path))
        connection.enable_load_extension(False)
        return connection

    def _init_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                embedding_json TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def _ensure_model(self) -> None:
        if self.model_loaded:
            return
        if not self.model_path:
            raise RuntimeError("Set SQLITE_AI_MODEL_PATH to an embedding-capable .gguf model file.")
        self.connection.execute("SELECT llm_model_load(?, '')", (self.model_path,))
        self.connection.execute("SELECT llm_context_create_embedding()")
        self.model_loaded = True

    def _embed(self, text: str) -> list[float]:
        row = self.connection.execute(
            "SELECT llm_embed_generate(?, 'json_output=1')",
            (text,),
        ).fetchone()
        if row is None or row[0] is None:
            raise RuntimeError("SQLite-AI returned no embedding.")
        return parse_embedding(row[0])

    def add(self, text: str) -> int:
        with self.lock:
            self._ensure_model()
            embedding = self._embed(text)
            cursor = self.connection.execute(
                "INSERT INTO entries (content, embedding_json) VALUES (?, ?)",
                (text, json.dumps(embedding)),
            )
            self.connection.commit()
            return int(cursor.lastrowid)

    def find_best_match(self, text: str):
        with self.lock:
            self._ensure_model()
            query_embedding = self._embed(text)
            rows = self.connection.execute(
                "SELECT id, content, embedding_json FROM entries ORDER BY id ASC"
            ).fetchall()

        best_match = None
        best_score = float("-inf")

        for row in rows:
            stored_embedding = [float(value) for value in json.loads(row["embedding_json"])]
            if len(stored_embedding) != len(query_embedding):
                continue

            score = cosine_similarity(query_embedding, stored_embedding)
            if score > best_score:
                best_score = score
                best_match = {
                    "id": row["id"],
                    "text": row["content"],
                    "score": round(score, 6),
                }

        return best_match


app = Flask(__name__)

try:
    STORE = EmbeddingStore(DB_PATH, MODEL_PATH, SQLITE_AI_PACKAGE)
    STARTUP_ERROR = None
except Exception as exc:  # pragma: no cover - startup guard for missing local deps
    STORE = None
    STARTUP_ERROR = str(exc)


@app.get("/")
def index():
    return page_response()


@app.post("/embed")
def embed_text_route():
    text = request_text()
    if not text:
        if wants_json():
            return jsonify({"error": "text is required"}), 400
        return page_response(error="text is required")
    if STORE is None:
        if wants_json():
            return jsonify({"error": STARTUP_ERROR}), 500
        return page_response(error=STARTUP_ERROR, embed_text=text)

    try:
        entry_id = STORE.add(text)
    except Exception as exc:
        if wants_json():
            return jsonify({"error": str(exc)}), 500
        return page_response(error=str(exc), embed_text=text)

    payload = {"stored": True, "id": entry_id, "text": text}
    if wants_json():
        return jsonify(payload)
    return page_response(message=json.dumps(payload, indent=2), embed_text=text)


@app.post("/request")
def request_route():
    text = request_text()
    if not text:
        if wants_json():
            return jsonify({"error": "text is required"}), 400
        return page_response(error="text is required")
    if STORE is None:
        if wants_json():
            return jsonify({"error": STARTUP_ERROR}), 500
        return page_response(error=STARTUP_ERROR, request_text=text)

    try:
        match = STORE.find_best_match(text)
    except Exception as exc:
        if wants_json():
            return jsonify({"error": str(exc)}), 500
        return page_response(error=str(exc), request_text=text)

    payload = {"query": text, "match": match}
    if wants_json():
        return jsonify(payload)
    return page_response(result=json.dumps(payload, indent=2), request_text=text)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)