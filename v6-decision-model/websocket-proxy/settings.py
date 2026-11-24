"""Editable defaults for the WebSocket proxy."""

from pathlib import Path

# model settings
MODEL = "d1-Omni-2B"
DECISION_MODEL_ENDPOINT = "http://192.168.50.60:1234"

# prompt dir
# where prompt files are stored
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# websocket port settings. Access your endpoint
# ws://localhost:9999/prompt-name
HOST = "localhost"
PORT = 9999
MAX_MESSAGE_BYTES = 64 * 1024 * 1024

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
LIVE_PROMPT = True