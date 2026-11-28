"""PyFunc discovery and execution routes for the prompting app."""

import importlib
import inspect

from flask import jsonify, request

from prompting_core import prompting_bp


def _to_bool(value):
    return str(value).lower() not in ("0", "false", "")


_TYPE_LABELS = {str: "str", int: "int", float: "float", bool: "bool"}
_TYPE_COERCE = {str: str, int: int, float: float, bool: _to_bool}
_PYFUNCS_MODULE = "pyfuncs"


def _load_pyfuncs():
    """Import or reload pyfuncs.py."""
    if _PYFUNCS_MODULE in importlib.sys.modules:
        return importlib.reload(importlib.sys.modules[_PYFUNCS_MODULE])
    return importlib.import_module(_PYFUNCS_MODULE)


def _introspect(module):
    """Return a JSON-friendly function catalogue for pyfuncs.py."""
    functions = []

    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_"):
            continue
        if fn.__module__ != module.__name__:
            continue

        signature = inspect.signature(fn)
        params = []

        for param_name, param in signature.parameters.items():
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                annotation = str

            entry = {
                "name": param_name,
                "type": _TYPE_LABELS.get(annotation, "str"),
            }
            if param.default is not inspect.Parameter.empty:
                entry["default"] = str(param.default)
            params.append(entry)

        return_annotation = signature.return_annotation
        functions.append(
            {
                "name": name,
                "params": params,
                "returns": _TYPE_LABELS.get(return_annotation, "str"),
                "doc": (inspect.getdoc(fn) or "").split("\n")[0],
            }
        )

    return functions


@prompting_bp.route("/functions/", strict_slashes=False)
def list_functions():
    """Return JSON descriptors for callable functions in pyfuncs.py."""
    try:
        module = _load_pyfuncs()
        return jsonify(_introspect(module))
    except Exception as exc:  # pragma: no cover - runtime import surface
        return jsonify({"error": str(exc)}), 500


@prompting_bp.route("/functions/call", methods=["POST"])
def call_function():
    """Call a named function from pyfuncs.py with JSON parameters."""
    body = request.get_json(silent=True) or {}
    function_name = body.get("function", "").strip()
    raw_params = body.get("params") or {}

    if not function_name:
        return jsonify({"result": None, "error": "no function specified"}), 400

    try:
        module = _load_pyfuncs()
    except Exception as exc:  # pragma: no cover - runtime import surface
        return (
            jsonify(
                {
                    "result": None,
                    "error": f"could not load pyfuncs: {exc}",
                }
            ),
            500,
        )

    fn = getattr(module, function_name, None)
    if fn is None or not callable(fn) or function_name.startswith("_"):
        return (
            jsonify(
                {
                    "result": None,
                    "error": f"unknown function: {function_name}",
                }
            ),
            404,
        )

    signature = inspect.signature(fn)
    kwargs = {}

    for param_name, param in signature.parameters.items():
        if param_name not in raw_params:
            if param.default is inspect.Parameter.empty:
                return (
                    jsonify(
                        {
                            "result": None,
                            "error": f"missing param: {param_name}",
                        }
                    ),
                    400,
                )
            continue

        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            annotation = str
        coerce = _TYPE_COERCE.get(annotation, str)

        try:
            kwargs[param_name] = coerce(raw_params[param_name])
        except (TypeError, ValueError) as exc:
            return (
                jsonify(
                    {
                        "result": None,
                        "error": f"bad param {param_name!r}: {exc}",
                    }
                ),
                422,
            )

    try:
        result = fn(**kwargs)
    except Exception as exc:  # pragma: no cover - runtime function execution
        return jsonify({"result": None, "error": str(exc)}), 500

    return jsonify({"result": str(result), "error": None})
