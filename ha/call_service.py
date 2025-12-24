#!/usr/bin/env python3
"""Call a Home Assistant service via WebSocket."""

import json
from shared import connect_and_auth


def main():
    ws = connect_and_auth()
    
    service_call = {
        "id": 1,
        "type": "call_service",
        "domain": "switch",
        "service": "turn_off",
        "service_data": {"entity_id": "switch.plug_a"},
        "return_response": False
    }
    
    ws.send(json.dumps(service_call))
    result = json.loads(ws.recv())
    
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"Context ID: {result['result']['context']['id']}")
    
    ws.close()


if __name__ == "__main__":
    main()
