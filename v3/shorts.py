"""The proxy handles comms to/from the ui and bots.

The frontend is a served websocket sevice.
"""
import json

async def send_json(websocket, **kw):
    return await websocket.send(json.dumps(kw))
