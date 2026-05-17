from __future__ import annotations

import os
import sqlite3

from flask import Flask, jsonify, render_template, request

from embed_tool import Embed


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "embed_tool_assets", "run_example.db")
MIN_SCORE = 0.6
TOP_K = 5
EMBED_PREFIX = "memory: "
RETRIEVE_PREFIX = "query: "

embed = Embed(
    db_path=DB_PATH,
    # model_path="C:/Users/jay/.lmstudio/models/jinaai/jina-embeddings-v5-text-small-retrieval/v5-small-retrieval-Q8_0.gguf",
    model_path="C:/Users/jay/.lmstudio/models/Abiray/zembed-1-Q4_K_M-GGUF/zembed-1-Q4_K_M.gguf",
    sqlite_ai_package="sqliteai.binaries.cpu",
    embed_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
    retrieve_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
    embed_prefix=EMBED_PREFIX,
    retrieve_prefix=RETRIEVE_PREFIX,
)

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", min_score=MIN_SCORE, top_k=TOP_K)


@app.post("/request")
def request_text():
    text = request.form.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    min_score_text = request.form.get("min_score", "").strip()
    top_k_text = request.form.get("top_k", "").strip()

    try:
        min_score = float(min_score_text) if min_score_text else MIN_SCORE
        top_k = int(top_k_text) if top_k_text else TOP_K
        results = embed.retrieve_many(text, min_score=min_score, top_k=top_k)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        status = 400 if isinstance(exc, ValueError) else 500
        return jsonify({"error": str(exc)}), status

    return jsonify({"results": results, "count": len(results)})


@app.post("/embed")
def embed_text():
    text = request.form.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    try:
        entry_id = embed.embed(text)
    except (sqlite3.Error, RuntimeError, ValueError) as exc:
        status = 400 if isinstance(exc, ValueError) else 500
        return jsonify({"error": str(exc)}), status

    return jsonify({"id": entry_id})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")