from __future__ import annotations

import json

from flask import Blueprint, jsonify, render_template, request

from embed_tool import EmbeddingStore


def request_text() -> str:
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        return str(payload.get("text", "")).strip()
    return request.form.get("text", "").strip()


def wants_json() -> bool:
    return request.is_json or request.headers.get("Accept", "").startswith("application/json")


def page_response(startup_error: str | None, **values):
    return render_template(
        "index.html",
        startup_error=startup_error,
        embed_text="",
        request_text="",
        message=None,
        result=None,
        error=None,
        **values,
    )


def create_blueprint(store: EmbeddingStore | None, startup_error: str | None) -> Blueprint:
    blueprint = Blueprint("text_embed", __name__)

    @blueprint.get("/")
    def index():
        return page_response(startup_error)

    @blueprint.post("/embed")
    def embed_text_route():
        text = request_text()
        if not text:
            if wants_json():
                return jsonify({"error": "text is required"}), 400
            return page_response(startup_error, error="text is required")
        if store is None:
            if wants_json():
                return jsonify({"error": startup_error}), 500
            return page_response(startup_error, error=startup_error, embed_text=text)

        try:
            entry_id = store.add(text)
        except Exception as exc:
            if wants_json():
                return jsonify({"error": str(exc)}), 500
            return page_response(startup_error, error=str(exc), embed_text=text)

        payload = {"stored": True, "id": entry_id, "text": text}
        if wants_json():
            return jsonify(payload)
        return page_response(startup_error, message=json.dumps(payload, indent=2), embed_text=text)

    @blueprint.post("/request")
    def request_route():
        text = request_text()
        if not text:
            if wants_json():
                return jsonify({"error": "text is required"}), 400
            return page_response(startup_error, error="text is required")
        if store is None:
            if wants_json():
                return jsonify({"error": startup_error}), 500
            return page_response(startup_error, error=startup_error, request_text=text)

        try:
            match = store.find_best_match(text)
        except Exception as exc:
            if wants_json():
                return jsonify({"error": str(exc)}), 500
            return page_response(startup_error, error=str(exc), request_text=text)

        payload = {"query": text, "match": match}
        if wants_json():
            return jsonify(payload)
        return page_response(startup_error, result=json.dumps(payload, indent=2), request_text=text)

    return blueprint