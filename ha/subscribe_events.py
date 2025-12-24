#!/usr/bin/env python3
"""Subscribe to Home Assistant events with callbacks."""

import json
import websocket
from _creds import WS_URL, ACCESS_TOKEN

message_id = 1


def on_message(ws, message):
    global message_id
    data = json.loads(message)
    msg_type = data.get("type")
    
    if msg_type == "auth_required":
        ws.send(json.dumps({"type": "auth", "access_token": ACCESS_TOKEN}))
    elif msg_type == "auth_ok":
        ws.send(json.dumps({"id": message_id, "type": "subscribe_events"}))
        message_id += 1
    elif msg_type == "event":
        event = data.get("event", {})
        print(f"\nEVENT: {event.get('event_type')}")
        print(json.dumps(event, indent=2))


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"Closed: {close_status_code}")


def main():
    ws = websocket.WebSocketApp(WS_URL, on_message=on_message,
                                 on_error=on_error, on_close=on_close)
    ws.run_forever()


if __name__ == "__main__":
    main()
