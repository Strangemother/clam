"""Endpoint registry and proxy routes for the prompting app."""

import requests as _requests
from flask import jsonify, request

from prompting_core import prompting_bp


ENDPOINT_CONFIGS = {
    "lmstudio": {
        "label": "LM Studio (LAN)",
        "url": "http://192.168.50.60:1234/api/v1/chat",
        "proxy": True,
        "models_url": "http://192.168.50.60:1234/",
        "load": {
            "model_configs": {
                "granite-4.1-8b": {
                    "context_length": 10_000,
                }
            }
        },
    },
    "digital-ocean": {
        "label": "Digital Ocean Agent",
        "url": (
            "https://etmvt72kt6sz2233rv2mwqmc.agents.do-ai.run/"
            "api/v1/chat/completions"
        ),
        "proxy": True,
        "api_format": "openai",
        "headers": {
            "Authorization": "Bearer qlKu-6agODOFr0s8vbYizlulxIN71ypG",
        },
    },
}


def _endpoint_base_url(cfg):
    """Return the upstream service base URL without chat/models suffixes."""
    base = (cfg.get("models_url") or cfg.get("url") or "").rstrip("/")
    for suffix in (
        "/api/v1/chat/completions",
        "/api/v1/chat",
        "/v1/chat/completions",
        "/v1/models",
        "/api/v1/models",
    ):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def _lmstudio_load_config_for_model(cfg, model_name):
    """Return the configured LM Studio load payload for a model."""
    load_cfg = cfg.get("load") or {}
    model_configs = load_cfg.get("model_configs") or {}
    return model_configs.get(model_name) or load_cfg.get("default_config")


def _lmstudio_model_matches(entry, model_name):
    """Match a requested model name against LM Studio list entries."""
    candidates = {
        str(entry.get("id") or "").strip(),
        str(entry.get("model") or "").strip(),
        str(entry.get("path") or "").strip(),
    }
    candidates.discard("")

    if model_name in candidates:
        return True

    loaded_instances = entry.get("loaded_instances") or []
    for instance in loaded_instances:
        if not isinstance(instance, dict):
            continue
        if str(instance.get("id") or "").strip() == model_name:
            return True

    return False


def _lmstudio_list_models(cfg, headers):
    """Fetch the LM Studio REST model list, including loaded_instances."""
    base_url = _endpoint_base_url(cfg)
    models_url = f"{base_url}/api/v1/models"
    request_headers = {
        key: value
        for key, value in headers.items()
        if key.lower() != "content-type"
    }

    resp = _requests.get(models_url, headers=request_headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        items = data.get("data")
        if isinstance(items, list):
            return items

    raise ValueError("unexpected LM Studio models payload")


def _lmstudio_model_is_loaded(cfg, model_name, headers):
    """Return True when LM Studio already has the requested model loaded."""
    for entry in _lmstudio_list_models(cfg, headers):
        if not isinstance(entry, dict):
            continue
        if not _lmstudio_model_matches(entry, model_name):
            continue

        loaded_instances = entry.get("loaded_instances") or []
        if isinstance(loaded_instances, list) and loaded_instances:
            return True
        if str(entry.get("status") or "").lower() == "loaded":
            return True

    return False


def _lmstudio_load_model(cfg, model_name, load_config, headers):
    """Explicitly load a model into LM Studio with a supplied config."""
    base_url = _endpoint_base_url(cfg)
    load_url = f"{base_url}/api/v1/models/load"
    payload = {"model": model_name, **dict(load_config or {})}
    payload.setdefault("echo_load_config", True)

    request_headers = dict(headers)
    request_headers["Content-Type"] = "application/json"

    resp = _requests.post(
        load_url,
        json=payload,
        headers=request_headers,
        timeout=300,
    )
    resp.raise_for_status()


def _ensure_lmstudio_model_loaded(cfg, payload, headers):
    """Pre-load configured LM Studio models before the first chat request."""
    model_name = str(payload.get("model") or "").strip()
    if not model_name:
        return

    load_config = _lmstudio_load_config_for_model(cfg, model_name)
    if not load_config:
        return

    try:
        if _lmstudio_model_is_loaded(cfg, model_name, headers):
            return
    except (_requests.RequestException, ValueError):
        pass

    _lmstudio_load_model(cfg, model_name, load_config, headers)


@prompting_bp.route("/endpoints/", strict_slashes=False)
def list_endpoints():
    """Return configured LLM endpoints without exposing sensitive headers."""
    result = []

    for key, cfg in ENDPOINT_CONFIGS.items():
        is_proxy = cfg.get("proxy", False)
        entry = {
            "key": key,
            "label": cfg["label"],
            "proxy": is_proxy,
            "api_format": cfg.get("api_format", "lmstudio"),
        }
        if not is_proxy:
            entry["url"] = cfg["url"]
        if "models_url" in cfg:
            entry["models_url"] = cfg["models_url"]
        result.append(entry)

    return jsonify(result)


@prompting_bp.route("/proxy/", strict_slashes=False, methods=["POST"])
def proxy_request():
    """Proxy an LLM chat request to a configured backend endpoint."""
    service = request.args.get("service", "").strip()
    cfg = ENDPOINT_CONFIGS.get(service)

    if not cfg:
        return (
            jsonify({"error": f"unknown service: {service!r}"}),
            400,
        )
    if not cfg.get("proxy"):
        return (
            jsonify(
                {"error": "endpoint is not configured as a proxy service"}
            ),
            400,
        )

    payload = request.get_json(silent=True) or {}
    headers = dict(cfg.get("headers", {}))
    headers["Content-Type"] = "application/json"

    try:
        if cfg.get("load"):
            _ensure_lmstudio_model_loaded(cfg, payload, headers)

        resp = _requests.post(
            cfg["url"],
            json=payload,
            headers=headers,
            timeout=120,
        )
        return jsonify(resp.json()), resp.status_code
    except _requests.Timeout:
        return jsonify({"error": "upstream request timed out"}), 504
    except ValueError as exc:
        return jsonify({"error": f"invalid upstream response: {exc}"}), 502
    except _requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 502
