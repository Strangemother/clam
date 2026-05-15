"""Compatibility module exporting the prompting blueprint.

The original monolithic implementation has been split into focused modules:

- prompting_prompts.py    — prompt files, layouts, and template rendering
- prompting_pyfuncs.py    — Python function discovery and execution
- prompting_proxy.py      — endpoint registry and LLM proxy routes
- prompting_grad_voice.py — Grad Voice helper logic and routes

Importing this module preserves the existing public surface used by app.py.
"""

import importlib

from prompting_core import prompting_bp


for module_name in (
    "prompting_prompts",
    "prompting_pyfuncs",
    "prompting_proxy",
    "prompting_grad_voice",
):
    importlib.import_module(module_name)


__all__ = ["prompting_bp"]
