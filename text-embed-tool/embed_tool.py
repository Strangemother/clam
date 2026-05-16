from __future__ import annotations

import importlib.resources
import json
import math
import os
import sqlite3
import zlib


class Embed:
    def __init__(
        self,
        db_path: str,
        model_path: str,
        sqlite_ai_package: str,
        embed_context: str,
        retrieve_context: str,
    ):
        if not db_path:
            raise ValueError("db_path is required")
        if not model_path:
            raise ValueError("model_path is required")
        if not sqlite_ai_package:
            raise ValueError("sqlite_ai_package is required")
        if not embed_context:
            raise ValueError("embed_context is required")
        if not retrieve_context:
            raise ValueError("retrieve_context is required")

        self.db_path = db_path
        self.model_path = model_path
        self.sqlite_ai_package = sqlite_ai_package
        self.embed_context = embed_context
        self.retrieve_context = retrieve_context
        self.context_created = False
        self.connection = self._connect()
        self._init_schema()
        self._load_model()

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row

        extension_path = importlib.resources.files(self.sqlite_ai_package) / "ai"
        connection.enable_load_extension(True)
        connection.load_extension(str(extension_path))
        connection.enable_load_extension(False)
        return connection

    def _load_model(self) -> None:
        self.connection.execute("SELECT llm_model_load(?, '')", (self.model_path,))

    def _init_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                crc INTEGER NOT NULL
            )
            """
        )
        
        self.connection.commit()

    def _set_context(self, context_settings: str) -> None:
        if self.context_created:
            self.connection.execute("SELECT llm_context_free()")
        self.connection.execute("SELECT llm_context_create_embedding(?)", (context_settings,))
        self.context_created = True

    def _parse_embedding(self, raw_value: str) -> list[float]:
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

    def _embedding(self, text: str, context_settings: str) -> list[float]:
        self._set_context(context_settings)
        row = self.connection.execute(
            "SELECT llm_embed_generate(?, 'json_output=1')",
            (text,),
        ).fetchone()
        if row is None or row[0] is None:
            raise RuntimeError("SQLite-AI returned no embedding.")
        return self._parse_embedding(row[0])

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        dot = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _crc(self, text: str) -> int:
        return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF

    def embed(self, text: str) -> int:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text is required")

        embedding = self._embedding(clean_text, self.embed_context)
        crc = self._crc(clean_text)
        cursor = self.connection.execute(
            "INSERT INTO entries (content, embedding_json, crc) VALUES (?, ?, ?)",
            (clean_text, json.dumps(embedding), crc),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def retrieve(self, text: str, min_score: float | None = None) -> dict[str, object] | None:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text is required")

        query_embedding = self._embedding(clean_text, self.retrieve_context)
        rows = self.connection.execute(
            "SELECT id, content, embedding_json, crc FROM entries ORDER BY id ASC"
        ).fetchall()

        best_match = None
        best_score = float("-inf")

        for row in rows:
            stored_embedding = [float(value) for value in json.loads(row["embedding_json"])]
            if len(stored_embedding) != len(query_embedding):
                continue

            score = self._cosine_similarity(query_embedding, stored_embedding)
            if score > best_score:
                best_score = score
                best_match = {
                    "id": row["id"],
                    "text": row["content"],
                    "crc": row["crc"],
                    "score": round(score, 6),
                }

        if best_match is None:
            return None

        if min_score is not None and best_score < min_score:
            return None

        return best_match