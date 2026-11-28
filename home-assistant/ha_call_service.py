#!/usr/bin/env python3
"""
Minimal Home Assistant WebSocket Service Call Example
Connects, authenticates, and calls a service action.
"""

import json
import websocket

# Configuration
WS_URL = "ws://homeassistant.local:8123/api/websocket"
ACCESS_TOKEN = "eyJhbGOSIsImlhdCuxg6sRbUvEl0"

# Connect
ws = websocket.create_connection(WS_URL)

# 1. Receive auth_required
msg = json.loads(ws.recv())
print(f"1. Received: {msg['type']}")

# 2. Send authentication
ws.send(json.dumps({"type": "auth", "access_token": ACCESS_TOKEN}))

# 3. Receive auth_ok
msg = json.loads(ws.recv())
print(f"2. Received: {msg['type']}")

# 4. Call service action
service_call = {
    "id": 1,
    "type": "call_service",
    "domain": "switch",
    "service": "turn_off",
    "service_data": {
        "entity_id": "switch.plug_a"
    },
    "return_response": False
}

print(f"\n3. Calling service: {service_call['domain']}.{service_call['service']}")
print(f"   Entity: {service_call['service_data']['entity_id']}")
ws.send(json.dumps(service_call))

# 5. Receive result
msg = json.loads(ws.recv())
print(f"\n4. Result:")
print(f"   Type: {msg['type']}")
print(f"   Success: {msg.get('success')}")
if msg.get('success'):
    print(f"   Context ID: {msg['result']['context']['id']}")
else:
    print(f"   Error: {msg.get('error')}")

# Close
ws.close()
print("\nDone!")
