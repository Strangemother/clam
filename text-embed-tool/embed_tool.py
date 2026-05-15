from __future__ import annotations

import importlib.resources
import json
import math
import os
import sqlite3
import threading


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
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
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
            raise RuntimeError("Set MODEL_PATH in app.py to an embedding-capable .gguf model file.")
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

    def find_best_match(self, text: str) -> dict[str, object] | None:
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