from __future__ import annotations

import importlib.resources
import json
import math
import os
import re
import sqlite3
import zlib


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "about",
    "as",
    "at",
    "be",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "tell",
    "that",
    "the",
    "this",
    "to",
    "what",
    "with",
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _lexical_score(query_text: str, content_text: str) -> float:
    query_lower = query_text.lower().strip()
    content_lower = content_text.lower().strip()

    if not query_lower or not content_lower:
        return 0.0

    if query_lower == content_lower:
        return 1.0

    if query_lower in content_lower:
        return 0.98

    query_tokens = [token for token in _tokens(query_text) if token not in STOPWORDS]
    if not query_tokens:
        query_tokens = _tokens(query_text)

    if not query_tokens:
        return 0.0

    content_tokens = set(_tokens(content_text))
    shared = len(set(query_tokens) & content_tokens)
    if shared == 0:
        return 0.0

    return shared / len(set(query_tokens))


class Embed:
    def __init__(
        self,
        db_path: str,
        model_path: str,
        sqlite_ai_package: str,
        embed_context: str,
        retrieve_context: str,
        embed_prefix: str = "",
        retrieve_prefix: str = "",
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
        self.embed_prefix = embed_prefix
        self.retrieve_prefix = retrieve_prefix
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

        crc = self._crc(clean_text)
        existing = self.connection.execute(
            "SELECT id FROM entries WHERE crc = ? AND content = ? LIMIT 1",
            (crc, clean_text),
        ).fetchone()
        if existing is not None:
            return int(existing["id"])

        embedding = self._embedding(f"{self.embed_prefix}{clean_text}", self.embed_context)
        cursor = self.connection.execute(
            "INSERT INTO entries (content, embedding_json, crc) VALUES (?, ?, ?)",
            (clean_text, json.dumps(embedding), crc),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def retrieve_many(
        self,
        text: str,
        min_score: float | None = None,
        top_k: int = 5,
    ) -> list[dict[str, object]]:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text is required")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        query_embedding = self._embedding(
            f"{self.retrieve_prefix}{clean_text}",
            self.retrieve_context,
        )
        rows = self.connection.execute(
            "SELECT id, content, embedding_json, crc FROM entries ORDER BY id ASC"
        ).fetchall()

        matches = []

        for row in rows:
            stored_embedding = [float(value) for value in json.loads(row["embedding_json"])]
            if len(stored_embedding) != len(query_embedding):
                continue

            vector_score = self._cosine_similarity(query_embedding, stored_embedding)
            lexical_score = _lexical_score(clean_text, row["content"])
            score = max(vector_score, lexical_score)

            if min_score is not None and score < min_score:
                continue

            matches.append(
                {
                    "id": row["id"],
                    "text": row["content"],
                    "crc": row["crc"],
                    "vector_score": round(vector_score, 6),
                    "lexical_score": round(lexical_score, 6),
                    "score": round(score, 6),
                }
            )

        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:top_k]

    def retrieve(self, text: str, min_score: float | None = None) -> dict[str, object] | None:
        matches = self.retrieve_many(text, min_score=min_score, top_k=1)
        if not matches:
            return None
        return matches[0]