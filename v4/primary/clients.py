"""# Clients

Client Register, maintains a dictionary of all websockets,
managed by the onboarding (set_register) and offboarding (drop_register)
within the main loop `run.py`.

Call on a brand-new socket:

    set_register(uuid, websocket)

Remove from register:

    drop_register(websocket.uuid)


"""

from http_tools import http_quick_get, http_post_json, http_get_json
import json
import requests

REGISTER = {}


def set_register(uuid, websocket):
    REGISTER[uuid] = websocket


def drop_register(uuid):
    del REGISTER[uuid]


def get_register(uuid):
    return REGISTER[uuid]

