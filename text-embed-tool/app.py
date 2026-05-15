from __future__ import annotations

import os

from flask import Flask

from embed_tool import EmbeddingStore
from routes import create_blueprint


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLASK_ASSETS_DIR = os.path.join(BASE_DIR)
TEMPLATES_DIR = os.path.join(FLASK_ASSETS_DIR, "templates")
STATIC_DIR = os.path.join(FLASK_ASSETS_DIR, "static")
EMBED_TOOL_ASSETS_DIR = os.path.join(BASE_DIR, "embed_tool_assets")

DB_PATH = os.path.join(EMBED_TOOL_ASSETS_DIR, "knowledge.db")
MODEL_PATH = "C:/Users/jay/.lmstudio/models/jinaai/jina-embeddings-v5-text-small-retrieval"
SQLITE_AI_PACKAGE = "sqliteai.binaries.cpu"
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True


def create_app() -> Flask:
    app = Flask(__name__)

    try:
        store = EmbeddingStore(DB_PATH, MODEL_PATH, SQLITE_AI_PACKAGE)
        startup_error = None
    except Exception as exc:  # pragma: no cover - startup guard for missing local deps
        store = None
        startup_error = str(exc)

    app.register_blueprint(create_blueprint(store, startup_error))
    return app


def main() -> None:
    app.run(host=HOST, port=PORT, debug=DEBUG)


app = create_app()


if __name__ == "__main__":
    main()