"""Grad Voice helpers and routes for the prompting app."""

import json
import mimetypes
import os
import re
from urllib.parse import quote

import requests as _requests
from flask import jsonify, request

from prompting_core import prompting_bp


_DEFAULT_GRAD_VOICE_URL = (
    "http://192.168.50.60:42004/gradio_api/call/generate_unified_tts"
)
GRAD_VOICE_URL = os.environ.get("GRAD_VOICE_URL", _DEFAULT_GRAD_VOICE_URL)
GRAD_VOICE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Cache-Control": "no-cache",
}

GRAD_VOICE_DEFAULT_INPUTS = {
    "text_input": "Hello from prompting.",
    "tts_engine": "Kokoro TTS",
    "audio_format": "wav",
    "chatterbox_ref_audio": None,
    "chatterbox_exaggeration": 0.5,
    "chatterbox_temperature": 0.8,
    "chatterbox_cfg_weight": 0.5,
    "chatterbox_chunk_size": 300,
    "chatterbox_seed": 0,
    "chatterbox_mtl_ref_audio": None,
    "chatterbox_mtl_language": "en",
    "chatterbox_mtl_exaggeration": 0.5,
    "chatterbox_mtl_temperature": 0.8,
    "chatterbox_mtl_cfg_weight": 0.5,
    "chatterbox_mtl_repetition_penalty": 2,
    "chatterbox_mtl_min_p": 0.05,
    "chatterbox_mtl_top_p": 1,
    "chatterbox_mtl_chunk_size": 300,
    "chatterbox_mtl_seed": 0,
    "kokoro_voice": "af_bella",
    "kokoro_speed": 1,
    "fish_ref_audio": None,
    "fish_ref_text": "",
    "fish_temperature": 0.8,
    "fish_top_p": 0.8,
    "fish_repetition_penalty": 1.1,
    "fish_max_tokens": 1024,
    "fish_seed": 0,
    "indextts_ref_audio": None,
    "indextts_temperature": 0.8,
    "indextts_seed": 0,
    "indextts2_ref_audio": None,
    "indextts2_emotion_mode": "audio_reference",
    "indextts2_emotion_audio": None,
    "indextts2_emotion_description": "",
    "indextts2_emo_alpha": 1,
    "indextts2_happy": 0,
    "indextts2_angry": 0,
    "indextts2_sad": 0,
    "indextts2_afraid": 0,
    "indextts2_disgusted": 0,
    "indextts2_melancholic": 0,
    "indextts2_surprised": 0,
    "indextts2_calm": 1,
    "indextts2_temperature": 0.8,
    "indextts2_top_p": 0.9,
    "indextts2_top_k": 50,
    "indextts2_repetition_penalty": 1.1,
    "indextts2_max_mel_tokens": 1500,
    "indextts2_seed": 0,
    "indextts2_use_random": False,
    "f5_ref_audio": None,
    "f5_ref_text": "",
    "f5_speed": 1,
    "f5_cross_fade": 0.15,
    "f5_remove_silence": False,
    "f5_seed": 0,
    "higgs_ref_audio": None,
    "higgs_ref_text": "",
    "higgs_voice_preset": "EMPTY",
    "higgs_system_prompt": "",
    "higgs_temperature": 1,
    "higgs_top_p": 0.95,
    "higgs_top_k": 50,
    "higgs_max_tokens": 1024,
    "higgs_ras_win_len": 7,
    "higgs_ras_win_max_num_repeat": 2,
    "kitten_voice": "expr-voice-2-f",
    "voxcpm_ref_audio": None,
    "voxcpm_ref_text": "",
    "voxcpm_cfg_value": 2,
    "voxcpm_inference_timesteps": 10,
    "voxcpm_normalize": True,
    "voxcpm_denoise": True,
    "voxcpm_retry_badcase": True,
    "voxcpm_retry_badcase_max_times": 3,
    "voxcpm_retry_badcase_ratio_threshold": 6,
    "voxcpm_seed": -1,
    "gain_db": 0,
    "enable_eq": False,
    "eq_bass": 0,
    "eq_mid": 0,
    "eq_treble": 0,
    "enable_reverb": False,
    "reverb_room": 0.3,
    "reverb_damping": 0.5,
    "reverb_wet": 0.3,
    "enable_echo": False,
    "echo_delay": 0.3,
    "echo_decay": 0.5,
    "enable_pitch": False,
    "pitch_semitones": 0,
}

GRAD_VOICE_VOICES = [
    {"value": "af_bella", "label": "Bella (af_bella)"},
    {"value": "bf_emma", "label": "Emma (bf_emma)"},
]

GRAD_VOICE_INDEXTTS2_DEFAULT_REF_AUDIO_PATH = (
    "G:\\pinokio\\api\\Ultimate-TTS-Studio.git\\cache\\GRADIO_TEMP_DIR"
    "\\05265ae741fc0e2066789758495c59ab2c5568bfd330336912ff5c098930ce0b"
    "\\tara_20250620_010154.wav"
)

GRAD_VOICE_INDEXTTS2_DEFAULTS = {
    "tts_engine": "IndexTTS2",
    "audio_format": "wav",
    "indextts2_ref_audio": GRAD_VOICE_INDEXTTS2_DEFAULT_REF_AUDIO_PATH,
    "indextts2_emotion_mode": "vector_control",
    "indextts2_emotion_audio": None,
    "indextts2_emotion_description": "excited and churlish",
    "indextts2_emo_alpha": 1,
    "indextts2_happy": 0,
    "indextts2_angry": 0,
    "indextts2_sad": 0.6,
    "indextts2_afraid": 0,
    "indextts2_disgusted": 0,
    "indextts2_melancholic": 1,
    "indextts2_surprised": 0,
    "indextts2_calm": 0.2,
    "indextts2_temperature": 0.8,
    "indextts2_top_p": 0.9,
    "indextts2_top_k": 50,
    "indextts2_repetition_penalty": 1.1,
    "indextts2_max_mel_tokens": 1500,
    "indextts2_seed": 0,
    "indextts2_use_random": False,
}


def _build_grad_voice_payload(text, overrides=None):
    """Build the positional request payload for the Grad Voice service."""
    inputs = dict(GRAD_VOICE_DEFAULT_INPUTS)
    inputs["text_input"] = text

    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if key in inputs:
                inputs[key] = value

    return {"data": list(inputs.values())}


def _normalize_grad_voice_selection(voice=None, options=None):
    """Return normalized Grad Voice options and the selected Kokoro voice."""
    clean_options = dict(options or {})
    selected_voice = str(voice or "").strip()
    if selected_voice:
        clean_options["kokoro_voice"] = selected_voice

    selected_voice = str(
        clean_options.get("kokoro_voice")
        or GRAD_VOICE_DEFAULT_INPUTS.get("kokoro_voice")
        or ""
    ).strip()
    return clean_options, selected_voice


def _grad_voice_base_url():
    """Return the base origin for the configured Grad Voice service."""
    marker = "/gradio_api/call/"
    url = GRAD_VOICE_URL.rstrip("/")
    if marker in url:
        return url.split(marker, 1)[0]
    return url


def _grad_voice_event_url(event_id):
    """Return the event-stream URL for a Grad Voice request."""
    return f"{GRAD_VOICE_URL.rstrip('/')}/{event_id}"


def _grad_voice_file_url(file_path):
    """Return the upstream file URL for a Gradio FileData path."""
    return f"{_grad_voice_base_url()}/gradio_api/file={file_path}"


def _grad_voice_upstream_config_urls():
    """Return likely config/info endpoints for the upstream Gradio app."""
    base_url = _grad_voice_base_url().rstrip("/")
    return [f"{base_url}/gradio_api/info", f"{base_url}/config"]


def _grad_voice_upload_urls():
    """Return likely upload endpoints for the upstream Gradio app."""
    base_url = _grad_voice_base_url().rstrip("/")
    return [f"{base_url}/gradio_api/upload", f"{base_url}/upload"]


def _looks_like_grad_voice_id(value):
    """Return True when a value looks like a Kokoro-style voice id."""
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r"[ab][fm]_[a-z0-9]+", value.strip().lower()))


def _voice_option_label(value):
    """Turn a voice id like af_bella into a user-friendly label."""
    voice_id = str(value or "").strip()
    if not voice_id:
        return ""

    parts = voice_id.split("_", 1)
    name = parts[1] if len(parts) > 1 else voice_id
    return f"{name.replace('_', ' ').title()} ({voice_id})"


def _extract_grad_voice_values_from_choices(choices):
    """Extract voice ids from a Gradio-style choices payload."""
    values = []
    if not isinstance(choices, list):
        return values

    for choice in choices:
        candidate = None
        if isinstance(choice, str):
            candidate = choice
        elif isinstance(choice, dict):
            for key in ("value", "name", "label", "id"):
                value = choice.get(key)
                if isinstance(value, str) and value:
                    candidate = value
                    break
        elif isinstance(choice, (list, tuple)) and choice:
            head = choice[0]
            if isinstance(head, str) and head:
                candidate = head

        if candidate and _looks_like_grad_voice_id(candidate):
            values.append(candidate.strip())

    return values


def _search_grad_voice_choices(value, found=None):
    """Recursively search a payload for Kokoro-style voice choice arrays."""
    if found is None:
        found = []

    if isinstance(value, dict):
        direct = _extract_grad_voice_values_from_choices(value.get("choices"))
        if direct:
            found.append(direct)
        for child in value.values():
            _search_grad_voice_choices(child, found)
    elif isinstance(value, list):
        direct = _extract_grad_voice_values_from_choices(value)
        if len(direct) > 1:
            found.append(direct)
        for item in value:
            _search_grad_voice_choices(item, found)

    return found


def _fetch_grad_voice_voices_from_upstream():
    """Best-effort voice discovery from the upstream Gradio app."""
    best = []

    for url in _grad_voice_upstream_config_urls():
        try:
            resp = _requests.get(
                url,
                headers={"Accept": "application/json"},
                timeout=(1, 2),
            )
            resp.raise_for_status()
            payload = resp.json()
        except (_requests.RequestException, ValueError):
            continue

        matches = _search_grad_voice_choices(payload)
        for values in matches:
            unique = []
            seen = set()
            for value in values:
                voice_id = str(value or "").strip()
                if not voice_id or voice_id in seen:
                    continue
                seen.add(voice_id)
                unique.append(voice_id)

            if len(unique) > len(best):
                best = unique

    return [
        {"value": voice_id, "label": _voice_option_label(voice_id)}
        for voice_id in best
    ]


def _gradio_path_name(file_path):
    """Return the filename portion of a Gradio file path."""
    raw = str(file_path or "").replace("\\", "/")
    return raw.rsplit("/", 1)[-1] if raw else ""


def _coerce_gradio_file_data(value):
    """Normalize a path, JSON string, or dict into Gradio FileData."""
    if value is None:
        return None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        if raw.startswith("{"):
            try:
                return _coerce_gradio_file_data(json.loads(raw))
            except ValueError:
                pass

        guessed_mime, _ = mimetypes.guess_type(raw)
        is_url = raw.startswith(("http://", "https://"))
        return {
            "path": None if is_url else raw,
            "url": raw if is_url else _grad_voice_file_url(raw),
            "orig_name": _gradio_path_name(raw) or None,
            "mime_type": guessed_mime,
            "meta": {"_type": "gradio.FileData"},
        }

    if not isinstance(value, dict):
        return None

    raw_path = str(value.get("path") or "").strip()
    raw_url = str(value.get("url") or "").strip()
    if not raw_path and not raw_url:
        return None

    result = dict(value)
    guessed_mime, _ = mimetypes.guess_type(raw_path or raw_url)
    result["path"] = raw_path or None
    result["url"] = raw_url or (_grad_voice_file_url(raw_path) if raw_path else None)
    result["orig_name"] = (
        str(value.get("orig_name") or "").strip()
        or _gradio_path_name(raw_path or raw_url)
        or None
    )
    result["mime_type"] = value.get("mime_type") or guessed_mime
    meta = value.get("meta") or {}
    result["meta"] = {**meta, "_type": "gradio.FileData"}
    return result


def _extract_gradio_upload_paths(payload):
    """Extract uploaded server paths from a Gradio upload response."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("files") or payload.get("data") or payload.get(
            "paths"
        ) or []
    else:
        items = []

    paths = []
    for item in items:
        if isinstance(item, str):
            path = item.strip()
        elif isinstance(item, dict):
            path = str(item.get("path") or item.get("name") or "").strip()
        else:
            path = ""

        if path:
            paths.append(path)

    return paths


def _upload_grad_voice_file_storage(file_storage):
    """Upload a Flask FileStorage object to the upstream Gradio app."""
    if file_storage is None or not str(file_storage.filename or "").strip():
        return None, None

    file_name = _gradio_path_name(file_storage.filename) or "upload.bin"
    mime_type = (
        str(getattr(file_storage, "mimetype", "") or "").strip()
        or "application/octet-stream"
    )

    try:
        file_bytes = file_storage.read()
    except Exception as exc:  # pragma: no cover - framework-dependent failure
        return None, ({"error": f"could not read upload: {exc}"}, 400)

    if not file_bytes:
        return None, ({"error": f"upload '{file_name}' was empty"}, 400)

    last_error = None
    for url in _grad_voice_upload_urls():
        try:
            resp = _requests.post(
                url,
                files=[("files", (file_name, file_bytes, mime_type))],
                timeout=120,
            )
            payload = resp.json()
        except _requests.Timeout:
            last_error = ({"error": "upstream upload timed out"}, 504)
            continue
        except ValueError as exc:
            last_error = (
                {"error": f"invalid upload response: {exc}", "endpoint": url},
                502,
            )
            continue
        except _requests.RequestException as exc:
            last_error = ({"error": str(exc), "endpoint": url}, 502)
            continue

        if not resp.ok:
            last_error = (
                {
                    "error": f"upload failed with status {resp.status_code}",
                    "endpoint": url,
                    "response": payload,
                },
                resp.status_code,
            )
            continue

        uploaded_paths = _extract_gradio_upload_paths(payload)
        if not uploaded_paths:
            last_error = (
                {
                    "error": "upload response did not include file paths",
                    "endpoint": url,
                    "response": payload,
                },
                502,
            )
            continue

        return (
            _coerce_gradio_file_data(
                {
                    "path": uploaded_paths[0],
                    "orig_name": file_name,
                    "mime_type": mime_type,
                    "meta": {"_type": "gradio.FileData"},
                }
            ),
            None,
        )

    return None, last_error or ({"error": "upload failed"}, 502)


def _build_grad_voice_indextts2_overrides(
    ref_audio=None,
    emotion_audio=None,
    options=None,
):
    """Build dedicated IndexTTS2 overrides for the shared Grad Voice route."""
    overrides = dict(GRAD_VOICE_INDEXTTS2_DEFAULTS)

    if isinstance(options, dict):
        for key, value in options.items():
            if key in GRAD_VOICE_DEFAULT_INPUTS:
                overrides[key] = value

    if ref_audio is not None:
        overrides["indextts2_ref_audio"] = ref_audio
    if emotion_audio is not None:
        overrides["indextts2_emotion_audio"] = emotion_audio

    overrides["indextts2_ref_audio"] = _coerce_gradio_file_data(
        overrides.get("indextts2_ref_audio")
    )
    overrides["indextts2_emotion_audio"] = _coerce_gradio_file_data(
        overrides.get("indextts2_emotion_audio")
    )
    return overrides


def _parse_gradio_event_stream(raw_text):
    """Parse a Gradio SSE response into a list of event/data pairs."""
    items = []
    current_event = None

    for line in raw_text.splitlines():
        if not line:
            continue
        if line.startswith("event: "):
            current_event = line[len("event: "):].strip() or None
            continue
        if not line.startswith("data: "):
            continue

        raw_data = line[len("data: "):]
        parsed = raw_data
        try:
            parsed = json.loads(raw_data)
        except ValueError:
            pass

        items.append({"event": current_event or "message", "data": parsed})
        current_event = None

    return items


def _collect_gradio_file_entities(value, found=None):
    """Collect all nested Gradio FileData dicts from a parsed payload."""
    if found is None:
        found = []

    if isinstance(value, dict):
        meta = value.get("meta") or {}
        if meta.get("_type") == "gradio.FileData":
            found.append(value)
        for child in value.values():
            _collect_gradio_file_entities(child, found)
    elif isinstance(value, list):
        for item in value:
            _collect_gradio_file_entities(item, found)

    return found


def _normalize_gradio_file_entities(payloads):
    """Convert nested Gradio FileData objects into a JSON-friendly list."""
    files = []
    seen = set()

    for entity in _collect_gradio_file_entities(payloads):
        path = str(entity.get("path") or "").strip()
        url = str(entity.get("url") or "").strip()
        key = path or url
        if not key or key in seen:
            continue
        seen.add(key)

        name = (
            str(entity.get("orig_name") or "").strip()
            or _gradio_path_name(path)
        )
        direct_url = _grad_voice_file_url(path) if path else (url or None)
        proxy_url = None
        if path:
            proxy_url = (
                f"/prompting/grad-voice/file/?path={quote(path, safe='')}"
            )

        files.append(
            {
                "path": path or None,
                "orig_name": name or None,
                "mime_type": entity.get("mime_type"),
                "size": entity.get("size"),
                "url": direct_url,
                "proxy_url": proxy_url,
            }
        )

    return files


def _request_grad_voice(text, voice=None, options=None):
    """Submit a Grad Voice request and return a JSON-friendly response."""
    clean_options, selected_voice = _normalize_grad_voice_selection(
        voice,
        options,
    )
    payload = _build_grad_voice_payload(text, clean_options)

    try:
        resp = _requests.post(
            GRAD_VOICE_URL,
            data=json.dumps(payload),
            headers=GRAD_VOICE_HEADERS,
            timeout=120,
        )
        data = resp.json()
    except _requests.Timeout:
        return {"error": "upstream request timed out"}, 504
    except ValueError as exc:
        return {"error": f"invalid upstream response: {exc}"}, 502
    except _requests.RequestException as exc:
        return {"error": str(exc)}, 502

    event_id = data.get("event_id") if isinstance(data, dict) else None
    response_body = {
        "ok": resp.ok,
        "event_id": event_id,
        "voice": selected_voice,
        "response": data,
    }
    return response_body, resp.status_code


def _wait_for_grad_voice_result(event_id, timeout=300):
    """Wait for a Grad Voice event to complete and normalize any files."""
    try:
        wait_timeout = max(float(timeout), 1.0)
    except (TypeError, ValueError):
        wait_timeout = 300.0

    try:
        resp = _requests.get(
            _grad_voice_event_url(event_id),
            headers={
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            },
            timeout=(10, wait_timeout),
        )
        raw = resp.text
    except _requests.Timeout:
        return (
            {
                "ok": False,
                "done": False,
                "event_id": event_id,
                "error": "upstream event wait timed out",
            },
            504,
        )
    except _requests.RequestException as exc:
        return {"error": str(exc), "event_id": event_id}, 502

    if not resp.ok:
        return (
            {
                "ok": False,
                "done": False,
                "event_id": event_id,
                "error": raw or f"upstream status {resp.status_code}",
            },
            resp.status_code,
        )

    entries = _parse_gradio_event_stream(raw)
    payloads = [entry["data"] for entry in entries]
    files = _normalize_gradio_file_entities(payloads)
    first_file_url = files[0]["proxy_url"] if files else None

    return (
        {
            "ok": True,
            "done": True,
            "event_id": event_id,
            "status_event": entries[-1]["event"] if entries else None,
            "payloads": payloads,
            "files": files,
            "first_file_url": first_file_url,
        },
        200,
    )


@prompting_bp.route("/grad-voice/", strict_slashes=False, methods=["POST"])
def grad_voice_request():
    """Send text to the configured Grad Voice endpoint."""
    body = request.get_json(silent=True) or {}
    raw_text = body.get("text")
    text = "" if raw_text is None else str(raw_text)

    if not text.strip():
        return jsonify({"error": "no text provided"}), 400

    response_body, status_code = _request_grad_voice(
        text,
        voice=body.get("voice"),
        options=body.get("options"),
    )
    return jsonify(response_body), status_code


@prompting_bp.route(
    "/grad-voice/indextts2/", strict_slashes=False, methods=["POST"]
)
def grad_voice_indextts2_request():
    """Send text to Grad Voice using dedicated IndexTTS2 defaults."""
    if request.files or request.form:
        raw_options = str(request.form.get("options") or "").strip()
        try:
            options = json.loads(raw_options) if raw_options else {}
        except ValueError:
            return jsonify({"error": "invalid options payload"}), 400

        body = {
            "text": request.form.get("text"),
            "ref_audio": request.form.get("ref_audio"),
            "emotion_audio": request.form.get("emotion_audio"),
            "options": options,
        }
    else:
        body = request.get_json(silent=True) or {}

    raw_text = body.get("text")
    text = "" if raw_text is None else str(raw_text)

    if not text.strip():
        return jsonify({"error": "no text provided"}), 400

    ref_audio = body.get("ref_audio")
    emotion_audio = body.get("emotion_audio")

    uploaded_ref_audio, upload_error = _upload_grad_voice_file_storage(
        request.files.get("ref_audio_upload")
    )
    if upload_error:
        return jsonify(upload_error[0]), upload_error[1]
    if uploaded_ref_audio is not None:
        ref_audio = uploaded_ref_audio

    uploaded_emotion_audio, upload_error = _upload_grad_voice_file_storage(
        request.files.get("emotion_audio_upload")
    )
    if upload_error:
        return jsonify(upload_error[0]), upload_error[1]
    if uploaded_emotion_audio is not None:
        emotion_audio = uploaded_emotion_audio

    overrides = _build_grad_voice_indextts2_overrides(
        ref_audio=ref_audio,
        emotion_audio=emotion_audio,
        options=body.get("options"),
    )
    response_body, status_code = _request_grad_voice(text, options=overrides)
    response_body["engine"] = "IndexTTS2"
    response_body["voice"] = None
    return jsonify(response_body), status_code


@prompting_bp.route("/grad-voice/voices/", strict_slashes=False)
def grad_voice_voices():
    """Return the voice catalogue for the Grad Voice node."""
    voices = _fetch_grad_voice_voices_from_upstream() or GRAD_VOICE_VOICES
    source = (
        "upstream" if voices and voices != GRAD_VOICE_VOICES else "fallback"
    )
    return jsonify(
        {
            "default": GRAD_VOICE_DEFAULT_INPUTS.get("kokoro_voice"),
            "voices": voices,
            "source": source,
        }
    )


@prompting_bp.route(
    "/grad-voice/result/", strict_slashes=False, methods=["POST"]
)
def grad_voice_result_request():
    """Wait for a Grad Voice event and return any produced files."""
    body = request.get_json(silent=True) or {}
    event_id = str(body.get("event_id") or "").strip()

    if not event_id:
        return jsonify({"error": "no event_id provided"}), 400

    response_body, status_code = _wait_for_grad_voice_result(
        event_id,
        body.get("timeout", 300),
    )
    return jsonify(response_body), status_code


@prompting_bp.route(
    "/grad-voice/generate/", strict_slashes=False, methods=["POST"]
)
def grad_voice_generate_request():
    """Submit text to Grad Voice and wait for the first audio file."""
    body = request.get_json(silent=True) or {}
    raw_text = body.get("text")
    text = "" if raw_text is None else str(raw_text)

    if not text.strip():
        return jsonify({"error": "no text provided"}), 400

    submit_body, submit_status = _request_grad_voice(
        text,
        voice=body.get("voice"),
        options=body.get("options"),
    )
    if submit_status >= 400:
        return jsonify(submit_body), submit_status

    event_id = str(submit_body.get("event_id") or "").strip()
    if not event_id:
        return (
            jsonify(
                {
                    "error": (
                        "grad voice response did not include an event_id"
                    ),
                    "submit": submit_body,
                }
            ),
            502,
        )

    result_body, result_status = _wait_for_grad_voice_result(
        event_id,
        body.get("timeout", 300),
    )
    result_body["voice"] = submit_body.get("voice")
    result_body["submit"] = submit_body
    return jsonify(result_body), result_status


@prompting_bp.route("/grad-voice/file/", strict_slashes=False)
def grad_voice_file_proxy():
    """Proxy a generated Grad Voice file through Flask."""
    file_path = str(request.args.get("path") or "").strip()
    if not file_path:
        return jsonify({"error": "no path provided"}), 400

    try:
        resp = _requests.get(
            _grad_voice_file_url(file_path),
            headers={"Accept": "*/*"},
            timeout=120,
        )
    except _requests.Timeout:
        return jsonify({"error": "upstream file request timed out"}), 504
    except _requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 502

    headers = {}
    for key in (
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Cache-Control",
    ):
        value = resp.headers.get(key)
        if value:
            headers[key] = value

    headers.setdefault("Content-Type", "application/octet-stream")
    headers.setdefault(
        "Content-Disposition",
        (
            f'inline; filename="{_gradio_path_name(file_path) or "audio.bin"}"'
        ),
    )

    return resp.content, resp.status_code, headers
