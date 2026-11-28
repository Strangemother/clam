#!/usr/bin/env python3
"""
Home Assistant Service Call Helper
Reusable function for calling HA services via WebSocket.
"""

import json
import websocket


def call_ha_service(domain, service, entity_id=None, service_data=None, return_response=False):
    """
    Call a Home Assistant service action.
    
    Args:
        domain: Service domain (e.g., "switch", "light", "automation")
        service: Service name (e.g., "turn_on", "turn_off", "toggle")
        entity_id: Single entity or list of entities (optional)
        service_data: Additional service data dict (optional)
        return_response: Whether to return response data (default: False)
    
    Returns:
        dict: Result message from Home Assistant
    """
    WS_URL = "ws://homeassistant.local:8123/api/websocket"
    ACCESS_TOKEN = "e2Q0Og6sRbUvEl0"
    
    # Connect
    ws = websocket.create_connection(WS_URL)
    
    # Auth flow
    ws.recv()  # auth_required
    ws.send(json.dumps({"type": "auth", "access_token": ACCESS_TOKEN}))
    ws.recv()  # auth_ok
    
    # Build service call
    call_msg = {
        "id": 1,
        "type": "call_service",
        "domain": domain,
        "service": service,
        "return_response": return_response
    }
    
    # Add service_data or target
    data = service_data or {}
    if entity_id:
        if isinstance(entity_id, str):
            data["entity_id"] = entity_id
        else:
            data["entity_id"] = entity_id
    
    if data:
        call_msg["service_data"] = data
    
    # Send and receive
    ws.send(json.dumps(call_msg))
    result = json.loads(ws.recv())
    
    ws.close()
    return result


if __name__ == "__main__":
    # Example usage:
    
    # Turn off a switch
    result = call_ha_service("switch", "turn_off", entity_id="switch.plug_a")
    print(f"Turn off switch: {result['success']}")
    
    # Turn on a light with brightness
    result = call_ha_service(
        "light", 
        "turn_on", 
        entity_id="light.kitchen",
        service_data={"brightness": 128}
    )
    print(f"Turn on light: {result['success']}")
    
    # Toggle multiple entities
    result = call_ha_service(
        "switch", 
        "toggle", 
        entity_id=["switch.plug_a", "switch.plug_b"]
    )
    print(f"Toggle switches: {result['success']}")
