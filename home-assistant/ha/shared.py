"""Shared utilities for Home Assistant WebSocket connections."""

import json
import websocket
from _creds import WS_URL, ACCESS_TOKEN


def connect_and_auth():
    """Connect to HA WebSocket and authenticate."""
    ws = websocket.create_connection(WS_URL)
    ws.recv()
    ws.send(json.dumps({"type": "auth", "access_token": ACCESS_TOKEN}))
    ws.recv()
    return ws
