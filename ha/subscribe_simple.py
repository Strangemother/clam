#!/usr/bin/env python3
"""Simple Home Assistant event subscriber."""

import json
from shared import connect_and_auth


def main():
    ws = connect_and_auth()
    ws.send(json.dumps({"id": 1, "type": "subscribe_events"}))
    ws.recv()
    
    print("Listening for events (Ctrl+C to exit)\n")
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg["type"] == "event":
                event = msg["event"]
                print(f"Event: {event['event_type']}")
                print(json.dumps(event, indent=2))
                print("-" * 50)
    except KeyboardInterrupt:
        pass
    finally:
        ws.close()


if __name__ == "__main__":
    main()
