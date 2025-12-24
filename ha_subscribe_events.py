#!/usr/bin/env python3
"""
Minimal Home Assistant WebSocket Event Subscriber
Connects, authenticates, and prints all events from the event bus.
"""

import json
import websocket

# Configuration
WS_URL = "ws://homeassistant.local:8123/api/websocket"
ACCESS_TOKEN = "eyJhbGciOiJIUz...gXJmXsNRF33DFOuxg6sRbUvEl0"

message_id = 1

def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    global message_id
    
    data = json.loads(message)
    msg_type = data.get("type")
    
    print(f"Received: {msg_type}")
    
    if msg_type == "auth_required":
        # Step 1: Authenticate with access token
        auth_msg = {
            "type": "auth",
            "access_token": ACCESS_TOKEN
        }
        ws.send(json.dumps(auth_msg))
        print("Sent authentication")
    
    elif msg_type == "auth_ok":
        # Step 2: Subscribe to all events
        subscribe_msg = {
            "id": message_id,
            "type": "subscribe_events"
            # Optional: "event_type": "state_changed"  # Uncomment to filter specific events
        }
        ws.send(json.dumps(subscribe_msg))
        print(f"Subscribed to events (id: {message_id})")
        message_id += 1
    
    elif msg_type == "result":
        print(f"Result: success={data.get('success')}")
    
    elif msg_type == "event":
        # Step 3: Print event messages
        event = data.get("event", {})
        event_type = event.get("event_type")
        print(f"\n{'='*50}")
        print(f"EVENT: {event_type}")
        print(json.dumps(event, indent=2))
        print('='*50)
    
    elif msg_type == "auth_invalid":
        print(f"Authentication failed: {data.get('message')}")
        ws.close()


def on_error(ws, error):
    """Handle WebSocket errors"""
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket connection close"""
    print(f"Connection closed: {close_status_code} - {close_msg}")


def on_open(ws):
    """Handle WebSocket connection open"""
    print("WebSocket connection opened")


if __name__ == "__main__":
    print(f"Connecting to {WS_URL}...")
    
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run forever (blocking)
    ws.run_forever()
