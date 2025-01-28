"""The proxy handles comms to/from the ui and bots.

The frontend is a served websocket sevice.
"""
import json
import time

async def send_json(websocket, **kw):

    await websocket.send(json.dumps(kw))
    # await websocket.drain()
