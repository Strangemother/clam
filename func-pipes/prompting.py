"""
prompting.py
────────────────────────────────────────────────────────────────────────────
Flask Blueprint for the /prompting sub-app.

Registers:
  GET  /prompting/               → serves prompting.html
    GET  /prompting/layouts/<path> → returns a saved layout JSON file
    POST /prompting/layouts/<path> → saves a layout JSON file under PROMPTS_DIR
  GET  /prompting/prompts/       → lists prompt files as JSON
  GET  /prompting/prompts/<path> → returns parsed prompt content/meta
  POST /prompting/prompts/render → renders a Jinja2 prompt template
    GET  /prompting/grad-voice/voices/ → lists known Grad Voice voices
    POST /prompting/grad-voice/    → sends text to the backend Grad Voice service

PROMPTS_DIR defaults to v5_2/prompts/ relative to this file's parent,
but can be overridden with the PROMPTS_DIR environment variable.
"""

import os
import json
import pathlib
import inspect
import importlib
import markdown
import requests as _requests
from datetime import datetime, timezone
from urllib.parse import quote

from jinja2 import Template, TemplateSyntaxError
from flask import Blueprint, render_template, jsonify, request

# ── prompts directory ────────────────────────────────────────────────────────

_DEFAULT_PROMPTS = pathlib.Path(__file__).parent.parent / 'v5_2' / 'prompts'
PROMPTS_DIR = pathlib.Path(os.environ.get('PROMPTS_DIR', str(_DEFAULT_PROMPTS)))

# ── endpoint configuration ───────────────────────────────────────────────────
#
# Each entry:
#   label      — human-readable name shown in the UI dropdown
#   url        — target URL for LLM calls (and model listing for direct endpoints)
#   proxy      — True  → calls go via /prompting/proxy/?service=<key> (Flask adds auth)
#              — False → frontend calls the URL directly
#   api_format — 'lmstudio' (default) or 'openai'
#                'openai'   → proxy translates LM Studio ↔ OpenAI messages format
#   headers    — extra request headers sent by the proxy (e.g. Authorization)
#   models_url — optional base URL used by ModelList for the model dropdown
#                (leave absent for proxy endpoints that don't expose a models API)
#   load       — optional LM Studio pre-load config keyed by selected model id
#
ENDPOINT_CONFIGS = {
    'lmstudio': {
        'label':      'LM Studio (LAN)',
        'url':        'http://192.168.50.60:1234/api/v1/chat',
        'proxy':      True,
        'models_url': 'http://192.168.50.60:1234/',
        'load': {
            # Add exact model ids here when they need an explicit pre-load config.
            # 'default_config' applies to any model not listed in 'model_configs'.
            # 'default_config': {'context_length': 16384},
            'model_configs': {
                # 'openai/gpt-oss-20b': {'context_length': 16384},
                'granite-4.1-8b': {
                    'context_length': 10_000
                }
            },
        },
    },
    'digital-ocean': {
        'label':   'Digital Ocean Agent',
        'url':     'https://etmvt72kt6sz2233rv2mwqmc.agents.do-ai.run/api/v1/chat/completions',
        'proxy':   True,
        'api_format': 'openai',
        'headers': {
            'Authorization': 'Bearer qlKu-6agODOFr0s8vbYizlulxIN71ypG',
        },
    },
}

# ── grad voice configuration ────────────────────────────────────────────────

_DEFAULT_GRAD_VOICE_URL = 'http://192.168.50.60:42003/gradio_api/call/generate_unified_tts'
GRAD_VOICE_URL = os.environ.get('GRAD_VOICE_URL', _DEFAULT_GRAD_VOICE_URL)
GRAD_VOICE_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Cache-Control': 'no-cache',
}

# Order matters here: the Gradio API expects the inputs as a positional array.
GRAD_VOICE_DEFAULT_INPUTS = {
    'text_input': 'Hello from prompting.',
    'tts_engine': 'Kokoro TTS',
    'audio_format': 'wav',
    'chatterbox_ref_audio': None,
    'chatterbox_exaggeration': 0.5,
    'chatterbox_temperature': 0.8,
    'chatterbox_cfg_weight': 0.5,
    'chatterbox_chunk_size': 300,
    'chatterbox_seed': 0,
    'chatterbox_mtl_ref_audio': None,
    'chatterbox_mtl_language': 'en',
    'chatterbox_mtl_exaggeration': 0.5,
    'chatterbox_mtl_temperature': 0.8,
    'chatterbox_mtl_cfg_weight': 0.5,
    'chatterbox_mtl_repetition_penalty': 2,
    'chatterbox_mtl_min_p': 0.05,
    'chatterbox_mtl_top_p': 1,
    'chatterbox_mtl_chunk_size': 300,
    'chatterbox_mtl_seed': 0,
    'kokoro_voice': 'af_bella',
    'kokoro_speed': 1,
    'fish_ref_audio': None,
    'fish_ref_text': '',
    'fish_temperature': 0.8,
    'fish_top_p': 0.8,
    'fish_repetition_penalty': 1.1,
    'fish_max_tokens': 1024,
    'fish_seed': 0,
    'indextts_ref_audio': None,
    'indextts_temperature': 0.8,
    'indextts_seed': 0,
    'indextts2_ref_audio': None,
    'indextts2_emotion_mode': 'audio_reference',
    'indextts2_emotion_audio': None,
    'indextts2_emotion_description': '',
    'indextts2_emo_alpha': 1,
    'indextts2_happy': 0,
    'indextts2_angry': 0,
    'indextts2_sad': 0,
    'indextts2_afraid': 0,
    'indextts2_disgusted': 0,
    'indextts2_melancholic': 0,
    'indextts2_surprised': 0,
    'indextts2_calm': 1,
    'indextts2_temperature': 0.8,
    'indextts2_top_p': 0.9,
    'indextts2_top_k': 50,
    'indextts2_repetition_penalty': 1.1,
    'indextts2_max_mel_tokens': 1500,
    'indextts2_seed': 0,
    'indextts2_use_random': False,
    'f5_ref_audio': None,
    'f5_ref_text': '',
    'f5_speed': 1,
    'f5_cross_fade': 0.15,
    'f5_remove_silence': False,
    'f5_seed': 0,
    'higgs_ref_audio': None,
    'higgs_ref_text': '',
    'higgs_voice_preset': 'EMPTY',
    'higgs_system_prompt': '',
    'higgs_temperature': 1,
    'higgs_top_p': 0.95,
    'higgs_top_k': 50,
    'higgs_max_tokens': 1024,
    'higgs_ras_win_len': 7,
    'higgs_ras_win_max_num_repeat': 2,
    'kitten_voice': 'expr-voice-2-f',
    'voxcpm_ref_audio': None,
    'voxcpm_ref_text': '',
    'voxcpm_cfg_value': 2,
    'voxcpm_inference_timesteps': 10,
    'voxcpm_normalize': True,
    'voxcpm_denoise': True,
    'voxcpm_retry_badcase': True,
    'voxcpm_retry_badcase_max_times': 3,
    'voxcpm_retry_badcase_ratio_threshold': 6,
    'voxcpm_seed': -1,
    'gain_db': 0,
    'enable_eq': False,
    'eq_bass': 0,
    'eq_mid': 0,
    'eq_treble': 0,
    'enable_reverb': False,
    'reverb_room': 0.3,
    'reverb_damping': 0.5,
    'reverb_wet': 0.3,
    'enable_echo': False,
    'echo_delay': 0.3,
    'echo_decay': 0.5,
    'enable_pitch': False,
    'pitch_semitones': 0,
}

GRAD_VOICE_VOICES = [
    {
        'value': 'af_bella',
        'label': 'Bella (af_bella)',
    },
    {
        'value': 'bf_emma',
        'label': 'Emma (bf_emma)',
    },
]

# ── Blueprint ────────────────────────────────────────────────────────────────

prompting_bp = Blueprint('prompting', __name__, url_prefix='/prompting')


# ── helpers ──────────────────────────────────────────────────────────────────

def _list_prompt_files():
    """Return a list of {name, path} dicts for every .md/.txt under PROMPTS_DIR."""
    if not PROMPTS_DIR.exists():
        return []
    files = sorted(PROMPTS_DIR.rglob('*.md')) + sorted(PROMPTS_DIR.rglob('*.txt'))
    prompts = []
    for f in files:
        if not f.is_file():
            continue
        rel   = f.relative_to(PROMPTS_DIR)
        label = f.name
        for ext in ('.prompt.md', '.prompt.txt', '.md', '.txt'):
            if label.lower().endswith(ext):
                label = label[: len(label) - len(ext)]
                break
        if len(rel.parts) > 1:
            label = ' / '.join(list(rel.parts[:-1]) + [label])
        prompts.append({'name': label, 'path': str(rel)})
    return prompts


def _parse_prompt_file(target: pathlib.Path) -> dict:
    """Parse a .md prompt file, strip meta header, return content + metadata."""
    raw = target.read_text(encoding='utf-8', errors='replace')
    md  = markdown.Markdown(extensions=['meta'])
    md.convert(raw)
    content = '\n'.join(md.lines).strip()
    meta    = {k: v for k, v in md.Meta.items()}

    def first(key, default=''):
        vals = meta.get(key) or []
        return vals[0] if vals else default

    stem = target.name
    for _ in target.suffixes:
        stem = pathlib.Path(stem).stem

    return {
        'content':     content,
        'description': first('description'),
        'title':       first('title', stem),
        'model':       first('models') or first('model'),
        'meta':        meta,
    }


def _safe_target(prompt_path: str):
    """Resolve prompt_path inside PROMPTS_DIR; return (target, error_response)."""
    target = (PROMPTS_DIR / prompt_path).resolve()
    if not str(target).startswith(str(PROMPTS_DIR.resolve())):
        return None, (jsonify({'error': 'invalid path'}), 400)
    if not target.exists():
        return None, (jsonify({'error': 'not found'}), 404)
    return target, None


def _safe_layout_target(layout_name: str):
    """Resolve a layout JSON file inside PROMPTS_DIR.

    Supports either:
    - an exact relative path such as ``self-2/self-2.prompting-layout``
    - a bare filename such as ``self-2.prompting-layout`` when that filename is unique
    """
    raw_name = (layout_name or '').strip()
    if not raw_name:
        return None, (jsonify({'error': 'no layout specified'}), 400)

    layout_path = raw_name if raw_name.lower().endswith('.json') else f'{raw_name}.json'
    root = PROMPTS_DIR.resolve()

    target = (PROMPTS_DIR / layout_path).resolve()
    if str(target).startswith(str(root)) and target.is_file():
        return target, None

    # If the user supplied only a bare name, search by filename under PROMPTS_DIR.
    if '/' not in raw_name and '\\' not in raw_name:
        basename = pathlib.Path(layout_path).name
        matches = []
        for candidate in PROMPTS_DIR.rglob(basename):
            resolved = candidate.resolve()
            if not str(resolved).startswith(str(root)):
                continue
            if resolved.is_file() and resolved not in matches:
                matches.append(resolved)

        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, (jsonify({
                'error': 'ambiguous layout name',
                'matches': [str(p.relative_to(root)) for p in matches],
            }), 409)

    return None, (jsonify({'error': 'layout not found'}), 404)


def _safe_layout_write_target(layout_name: str):
    """Resolve a layout JSON path for writing inside PROMPTS_DIR."""
    raw_name = (layout_name or '').strip()
    if not raw_name:
        return None, (jsonify({'error': 'no layout specified'}), 400)

    layout_path = raw_name if raw_name.lower().endswith('.json') else f'{raw_name}.json'
    target = (PROMPTS_DIR / layout_path).resolve()
    root = PROMPTS_DIR.resolve()

    if not str(target).startswith(str(root)):
        return None, (jsonify({'error': 'invalid path'}), 400)

    return target, None


def _endpoint_base_url(cfg: dict) -> str:
    """Return the upstream service base URL without chat/models suffixes."""
    base = (cfg.get('models_url') or cfg.get('url') or '').rstrip('/')
    for suffix in (
        '/api/v1/chat/completions',
        '/api/v1/chat',
        '/v1/chat/completions',
        '/v1/models',
        '/api/v1/models',
    ):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def _lmstudio_load_config_for_model(cfg: dict, model_name: str):
    """Return the configured load payload for a model, if any."""
    load_cfg = cfg.get('load') or {}
    model_configs = load_cfg.get('model_configs') or {}
    return model_configs.get(model_name) or load_cfg.get('default_config')


def _lmstudio_model_matches(entry: dict, model_name: str) -> bool:
    """Match a model id against the ids returned by LM Studio's list endpoint."""
    candidates = {
        str(entry.get('id') or '').strip(),
        str(entry.get('model') or '').strip(),
        str(entry.get('path') or '').strip(),
    }
    candidates.discard('')
    if model_name in candidates:
        return True

    loaded_instances = entry.get('loaded_instances') or []
    for instance in loaded_instances:
        if not isinstance(instance, dict):
            continue
        if str(instance.get('id') or '').strip() == model_name:
            return True
    return False


def _lmstudio_list_models(cfg: dict, headers: dict) -> list:
    """Fetch the LM Studio REST model list, including loaded_instances."""
    base_url = _endpoint_base_url(cfg)
    models_url = f'{base_url}/api/v1/models'
    request_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
    resp = _requests.get(models_url, headers=request_headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        items = data.get('data')
        if isinstance(items, list):
            return items
    raise ValueError('unexpected LM Studio models payload')


def _lmstudio_model_is_loaded(cfg: dict, model_name: str, headers: dict) -> bool:
    """Return True when LM Studio already has the requested model loaded."""
    for entry in _lmstudio_list_models(cfg, headers):
        if not isinstance(entry, dict):
            continue
        if not _lmstudio_model_matches(entry, model_name):
            continue
        loaded_instances = entry.get('loaded_instances') or []
        if isinstance(loaded_instances, list) and loaded_instances:
            return True
        if str(entry.get('status') or '').lower() == 'loaded':
            return True
    return False


def _lmstudio_load_model(cfg: dict, model_name: str, load_config: dict, headers: dict):
    """Explicitly load a model into LM Studio with a caller-supplied config."""
    base_url = _endpoint_base_url(cfg)
    load_url = f'{base_url}/api/v1/models/load'
    payload = {'model': model_name, **dict(load_config or {})}
    payload.setdefault('echo_load_config', True)
    request_headers = dict(headers)
    request_headers['Content-Type'] = 'application/json'

    resp = _requests.post(load_url, json=payload, headers=request_headers, timeout=300)
    resp.raise_for_status()


def _ensure_lmstudio_model_loaded(cfg: dict, payload: dict, headers: dict):
    """Pre-load configured LM Studio models before the first chat request."""
    model_name = str(payload.get('model') or '').strip()
    if not model_name:
        return

    load_config = _lmstudio_load_config_for_model(cfg, model_name)
    if not load_config:
        return

    try:
        if _lmstudio_model_is_loaded(cfg, model_name, headers):
            return
    except (_requests.RequestException, ValueError):
        # If state inspection fails, still try an explicit load so autoload does
        # not bypass the requested context configuration.
        pass

    _lmstudio_load_model(cfg, model_name, load_config, headers)


def _build_grad_voice_payload(text: str, overrides=None) -> dict:
    """Build the positional Gradio request payload for the Grad Voice service."""
    inputs = dict(GRAD_VOICE_DEFAULT_INPUTS)
    inputs['text_input'] = text

    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if key in inputs:
                inputs[key] = value

    return {'data': list(inputs.values())}


def _grad_voice_base_url() -> str:
    """Return the base origin for the configured Grad Voice service."""
    marker = '/gradio_api/call/'
    url = GRAD_VOICE_URL.rstrip('/')
    if marker in url:
        return url.split(marker, 1)[0]
    return url


def _grad_voice_event_url(event_id: str) -> str:
    """Return the event-stream URL for a Grad Voice request."""
    return f"{GRAD_VOICE_URL.rstrip('/')}/{event_id}"


def _grad_voice_file_url(file_path: str) -> str:
    """Return the upstream file URL for a Gradio FileData path."""
    return f"{_grad_voice_base_url()}/gradio_api/file={file_path}"


def _gradio_path_name(file_path: str) -> str:
    """Return the filename portion of a Gradio file path."""
    raw = str(file_path or '').replace('\\', '/')
    return raw.rsplit('/', 1)[-1] if raw else ''


def _parse_gradio_event_stream(raw_text: str) -> list:
    """Parse a Gradio SSE response into a list of event/data pairs."""
    items = []
    current_event = None

    for line in raw_text.splitlines():
        if not line:
            continue
        if line.startswith('event: '):
            current_event = line[len('event: '):].strip() or None
            continue
        if not line.startswith('data: '):
            continue

        raw_data = line[len('data: '):]
        parsed = raw_data
        try:
            parsed = json.loads(raw_data)
        except ValueError:
            pass

        items.append({
            'event': current_event or 'message',
            'data': parsed,
        })
        current_event = None

    return items


def _collect_gradio_file_entities(value, found=None):
    """Collect all nested Gradio FileData dicts from a parsed payload."""
    if found is None:
        found = []

    if isinstance(value, dict):
        meta = value.get('meta') or {}
        if meta.get('_type') == 'gradio.FileData':
            found.append(value)
        for child in value.values():
            _collect_gradio_file_entities(child, found)
    elif isinstance(value, list):
        for item in value:
            _collect_gradio_file_entities(item, found)

    return found


def _normalize_gradio_file_entities(payloads) -> list:
    """Convert nested Gradio FileData objects into a JSON-friendly list."""
    files = []
    seen = set()

    for entity in _collect_gradio_file_entities(payloads):
        path = str(entity.get('path') or '').strip()
        url = str(entity.get('url') or '').strip()
        key = path or url
        if not key or key in seen:
            continue
        seen.add(key)

        name = str(entity.get('orig_name') or '').strip() or _gradio_path_name(path)
        direct_url = _grad_voice_file_url(path) if path else (url or None)
        proxy_url = None
        if path:
            proxy_url = f"/prompting/grad-voice/file/?path={quote(path, safe='')}"

        files.append({
            'path': path or None,
            'orig_name': name or None,
            'mime_type': entity.get('mime_type'),
            'size': entity.get('size'),
            'url': direct_url,
            'proxy_url': proxy_url,
        })

    return files


# ── routes ───────────────────────────────────────────────────────────────────

@prompting_bp.route('/', strict_slashes=False)
def index():
    return render_template('prompting.html')


@prompting_bp.route('/layouts/<path:layout_name>', strict_slashes=False)
def get_layout(layout_name):
    """Return a prompting layout JSON file from PROMPTS_DIR."""
    target, err = _safe_layout_target(layout_name)
    if err:
        return err
    return target.read_text(encoding='utf-8', errors='replace'), 200, {
        'Content-Type': 'application/json'
    }


@prompting_bp.route('/layouts/<path:layout_name>', strict_slashes=False, methods=['POST'])
def save_layout(layout_name):
    """Save a prompting layout JSON file inside PROMPTS_DIR."""
    target, err = _safe_layout_write_target(layout_name)
    if err:
        return err

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({'error': 'invalid json payload'}), 400

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        jsonify(payload).get_data(as_text=True) + '\n',
        encoding='utf-8',
    )

    return jsonify({
        'ok': True,
        'path': str(target.relative_to(PROMPTS_DIR.resolve())),
    })


@prompting_bp.route('/prompts/', strict_slashes=False)
def list_prompts():
    """Return JSON list of all prompt files under PROMPTS_DIR."""
    return jsonify(_list_prompt_files())


@prompting_bp.route('/prompts/<path:prompt_path>')
def get_prompt(prompt_path):
    """Return parsed prompt data as JSON (content, title, description, model, meta)."""
    target, err = _safe_target(prompt_path)
    if err:
        return err
    return jsonify(_parse_prompt_file(target))


@prompting_bp.route('/prompts/render', methods=['POST'])
def render_prompt():
    """Render a Jinja2 prompt template with provided variables.

    POST body (JSON):
      template  — raw template string  (required unless 'path' given)
      path      — prompt file path     (alternative to 'template')
      vars      — dict of variables    (optional)

    Always injects:  timestamp (UTC ISO-8601)

    Returns: { rendered: str, error: null }  or  { rendered: null, error: str }
    """
    body         = request.get_json(silent=True) or {}
    template_str = body.get('template')
    prompt_path  = body.get('path')
    variables    = dict(body.get('vars') or {})
    variables.setdefault('timestamp', datetime.now(timezone.utc).isoformat())

    if not template_str and prompt_path:
        target, err = _safe_target(prompt_path)
        if err:
            return err
        template_str = _parse_prompt_file(target)['content']

    if not template_str:
        return jsonify({'rendered': None, 'error': 'no template provided'}), 400

    try:
        rendered = Template(template_str).render(**variables)
    except TemplateSyntaxError as e:
        return jsonify({'rendered': None, 'error': f'template error: {e}'}), 422

    return jsonify({'rendered': rendered, 'error': None})


# ── pyfunc helpers ────────────────────────────────────────────────────────────

# Map Python annotation types → JSON-friendly label
_TYPE_LABELS = {str: 'str', int: 'int', float: 'float', bool: 'bool'}
_TYPE_COERCE  = {str: str,  int: int,   float: float,   bool: lambda v: str(v).lower() not in ('0', 'false', '')}

_PYFUNCS_MODULE = 'pyfuncs'  # module name, importable from the Flask cwd


def _load_pyfuncs():
    """Import (or reload) pyfuncs.py and return the module object."""
    if _PYFUNCS_MODULE in importlib.sys.modules:
        return importlib.reload(importlib.sys.modules[_PYFUNCS_MODULE])
    return importlib.import_module(_PYFUNCS_MODULE)


def _introspect(module) -> list:
    """Return a list of function descriptors from the module."""
    functions = []
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if name.startswith('_'):
            continue
        if fn.__module__ != module.__name__:
            continue          # skip re-exported symbols from other modules
        sig    = inspect.signature(fn)
        params = []
        for pname, param in sig.parameters.items():
            ann = param.annotation
            if ann is inspect.Parameter.empty:
                ann = str
            label = _TYPE_LABELS.get(ann, 'str')
            entry = {'name': pname, 'type': label}
            if param.default is not inspect.Parameter.empty:
                entry['default'] = str(param.default)
            params.append(entry)
        ret_ann = sig.return_annotation
        functions.append({
            'name':    name,
            'params':  params,
            'returns': _TYPE_LABELS.get(ret_ann, 'str'),
            'doc':     (inspect.getdoc(fn) or '').split('\n')[0],
        })
    return functions


# ── pyfunc routes ─────────────────────────────────────────────────────────────

@prompting_bp.route('/functions/', strict_slashes=False)
def list_functions():
    """Return JSON list of all callable functions from pyfuncs.py"""
    try:
        module = _load_pyfuncs()
        return jsonify(_introspect(module))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@prompting_bp.route('/functions/call', methods=['POST'])
def call_function():
    """Call a named function from pyfuncs.py with the given params.

    POST body (JSON):
      function  — function name (str, required)
      params    — dict of parameter_name → value (optional, defaults to {})

    Returns: { result: str, error: null }  or  { result: null, error: str }
    """
    body      = request.get_json(silent=True) or {}
    fn_name   = body.get('function', '').strip()
    raw_params = body.get('params') or {}

    if not fn_name:
        return jsonify({'result': None, 'error': 'no function specified'}), 400

    try:
        module = _load_pyfuncs()
    except Exception as e:
        return jsonify({'result': None, 'error': f'could not load pyfuncs: {e}'}), 500

    fn = getattr(module, fn_name, None)
    if fn is None or not callable(fn) or fn_name.startswith('_'):
        return jsonify({'result': None, 'error': f'unknown function: {fn_name}'}), 404

    # Coerce each param to its annotated type
    sig    = inspect.signature(fn)
    kwargs = {}
    for pname, param in sig.parameters.items():
        if pname not in raw_params:
            if param.default is inspect.Parameter.empty:
                return jsonify({'result': None, 'error': f'missing param: {pname}'}), 400
            continue   # use the default
        ann    = param.annotation if param.annotation is not inspect.Parameter.empty else str
        coerce = _TYPE_COERCE.get(ann, str)
        try:
            kwargs[pname] = coerce(raw_params[pname])
        except (ValueError, TypeError) as e:
            return jsonify({'result': None, 'error': f'bad param {pname!r}: {e}'}), 422

    try:
        result = fn(**kwargs)
        return jsonify({'result': str(result), 'error': None})
    except Exception as e:
        return jsonify({'result': None, 'error': str(e)}), 500


# ── endpoint registry routes ──────────────────────────────────────────────────

@prompting_bp.route('/endpoints/', strict_slashes=False)
def list_endpoints():
    """Return the set of configured LLM endpoints (no sensitive headers exposed).

    Returns a list of:
      key        — config key used as panel.endpointKey
      label      — human-readable name for the UI dropdown
      proxy      — true if calls are routed through /prompting/proxy/
      models_url — base URL for model-list fetching (absent for proxy endpoints)
    """
    result = []
    for key, cfg in ENDPOINT_CONFIGS.items():
        is_proxy = cfg.get('proxy', False)
        entry = {
            'key':        key,
            'label':      cfg['label'],
            'proxy':      is_proxy,
            'api_format': cfg.get('api_format', 'lmstudio'),
        }
        if not is_proxy:
            # Expose the chat URL only for direct endpoints (no auth headers to protect)
            entry['url'] = cfg['url']
        if 'models_url' in cfg:
            entry['models_url'] = cfg['models_url']
        result.append(entry)
    return jsonify(result)


@prompting_bp.route('/proxy/', strict_slashes=False, methods=['POST'])
def proxy_request():
    """Proxy an LLM chat request to a configured backend endpoint.

    Query params:
      service  — key from ENDPOINT_CONFIGS (required)

    POST body: standard chat payload forwarded verbatim to the target URL.
    The proxy adds authentication headers from the endpoint config before sending.

    Returns the target service's JSON response with its original HTTP status code.
    """
    service = request.args.get('service', '').strip()
    cfg     = ENDPOINT_CONFIGS.get(service)

    if not cfg:
        return jsonify({'error': f'unknown service: {service!r}'}), 400
    if not cfg.get('proxy'):
        return jsonify({'error': 'endpoint is not configured as a proxy service'}), 400

    payload = request.get_json(silent=True) or {}
    headers = dict(cfg.get('headers', {}))
    headers['Content-Type'] = 'application/json'

    # The Chat class already sends the correct api_format payload, so the proxy
    # only needs to add auth headers and forward. No translation required.
    try:
        if cfg.get('load'):
            _ensure_lmstudio_model_loaded(cfg, payload, headers)

        resp = _requests.post(cfg['url'], json=payload, headers=headers, timeout=120)
        return jsonify(resp.json()), resp.status_code
    except _requests.Timeout:
        return jsonify({'error': 'upstream request timed out'}), 504
    except ValueError as e:
        return jsonify({'error': f'invalid upstream response: {e}'}), 502
    except _requests.RequestException as e:
        return jsonify({'error': str(e)}), 502


@prompting_bp.route('/grad-voice/', strict_slashes=False, methods=['POST'])
def grad_voice_request():
    """Send text to the configured Grad Voice Gradio endpoint."""
    body = request.get_json(silent=True) or {}
    raw_text = body.get('text')
    text = '' if raw_text is None else str(raw_text)

    if not text.strip():
        return jsonify({'error': 'no text provided'}), 400

    options = dict(body.get('options') or {})
    selected_voice = str(body.get('voice') or '').strip()
    if selected_voice:
        options['kokoro_voice'] = selected_voice
    selected_voice = str(
        options.get('kokoro_voice') or GRAD_VOICE_DEFAULT_INPUTS.get('kokoro_voice') or ''
    ).strip()

    payload = _build_grad_voice_payload(text, options)

    try:
        resp = _requests.post(
            GRAD_VOICE_URL,
            data=json.dumps(payload),
            headers=GRAD_VOICE_HEADERS,
            timeout=120,
        )
        data = resp.json()
    except _requests.Timeout:
        return jsonify({'error': 'upstream request timed out'}), 504
    except ValueError as e:
        return jsonify({'error': f'invalid upstream response: {e}'}), 502
    except _requests.RequestException as e:
        return jsonify({'error': str(e)}), 502

    event_id = data.get('event_id') if isinstance(data, dict) else None
    response_body = {
        'ok': resp.ok,
        'event_id': event_id,
        'voice': selected_voice,
        'response': data,
    }
    if not resp.ok:
        return jsonify(response_body), resp.status_code

    return jsonify(response_body), resp.status_code


@prompting_bp.route('/grad-voice/voices/', strict_slashes=False)
def grad_voice_voices():
    """Return the configured voice catalogue for the Grad Voice node."""
    return jsonify({
        'default': GRAD_VOICE_DEFAULT_INPUTS.get('kokoro_voice'),
        'voices': GRAD_VOICE_VOICES,
    })


@prompting_bp.route('/grad-voice/result/', strict_slashes=False, methods=['POST'])
def grad_voice_result_request():
    """Wait for a Grad Voice event to complete and return any produced files."""
    body = request.get_json(silent=True) or {}
    event_id = str(body.get('event_id') or '').strip()

    if not event_id:
        return jsonify({'error': 'no event_id provided'}), 400

    timeout = body.get('timeout', 300)
    try:
        timeout = max(float(timeout), 1.0)
    except (TypeError, ValueError):
        timeout = 300.0

    try:
        resp = _requests.get(
            _grad_voice_event_url(event_id),
            headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
            },
            timeout=(10, timeout),
        )
        raw = resp.text
    except _requests.Timeout:
        return jsonify({
            'ok': False,
            'done': False,
            'event_id': event_id,
            'error': 'upstream event wait timed out',
        }), 504
    except _requests.RequestException as e:
        return jsonify({'error': str(e), 'event_id': event_id}), 502

    if not resp.ok:
        return jsonify({
            'ok': False,
            'done': False,
            'event_id': event_id,
            'error': raw or f'upstream status {resp.status_code}',
        }), resp.status_code

    entries = _parse_gradio_event_stream(raw)
    payloads = [entry['data'] for entry in entries]
    files = _normalize_gradio_file_entities(payloads)
    first_file_url = files[0]['proxy_url'] if files else None

    return jsonify({
        'ok': True,
        'done': True,
        'event_id': event_id,
        'status_event': entries[-1]['event'] if entries else None,
        'payloads': payloads,
        'files': files,
        'first_file_url': first_file_url,
    })


@prompting_bp.route('/grad-voice/file/', strict_slashes=False)
def grad_voice_file_proxy():
    """Proxy a generated Grad Voice file back through Flask."""
    file_path = str(request.args.get('path') or '').strip()
    if not file_path:
        return jsonify({'error': 'no path provided'}), 400

    try:
        resp = _requests.get(
            _grad_voice_file_url(file_path),
            headers={'Accept': '*/*'},
            timeout=120,
        )
    except _requests.Timeout:
        return jsonify({'error': 'upstream file request timed out'}), 504
    except _requests.RequestException as e:
        return jsonify({'error': str(e)}), 502

    headers = {}
    for key in ('Content-Type', 'Content-Length', 'Content-Disposition', 'Cache-Control'):
        value = resp.headers.get(key)
        if value:
            headers[key] = value

    headers.setdefault('Content-Type', 'application/octet-stream')
    headers.setdefault(
        'Content-Disposition',
        f'inline; filename="{_gradio_path_name(file_path) or "audio.bin"}"',
    )

    return resp.content, resp.status_code, headers
