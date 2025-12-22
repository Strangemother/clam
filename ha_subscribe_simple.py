#!/usr/bin/env python3
"""
Ultra-minimal Home Assistant WebSocket Event Subscriber
"""

import json
import websocket

WS_URL = "ws://homeassistant.local:8123/api/websocket"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"

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

# 4. Subscribe to events
ws.send(json.dumps({"id": 1, "type": "subscribe_events"}))

# 5. Receive subscription confirmation
msg = json.loads(ws.recv())
print(f"3. Received: {msg['type']} - success: {msg.get('success')}")

# 6. Print all events
print("\n=== Listening for events (Ctrl+C to exit) ===\n")
try:
    while True:
        msg = json.loads(ws.recv())
        if msg["type"] == "event":
            event = msg["event"]
            print(f"Event: {event['event_type']}")
            print(json.dumps(event, indent=2))
            print("-" * 50)
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    ws.close()
