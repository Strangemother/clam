#!/usr/bin/env python3
"""Reusable helper for calling HA services."""

import json
from shared import connect_and_auth


def call_service(domain, service, entity_id=None, service_data=None,
                 return_response=False):
    """Call a Home Assistant service.
    
    Args:
        domain: Service domain (e.g., "switch", "light")
        service: Service name (e.g., "turn_on", "turn_off")
        entity_id: Single entity or list of entities
        service_data: Additional service data dict
        return_response: Whether to return response data
    
    Returns:
        dict: Result message from Home Assistant
    """
    ws = connect_and_auth()
    
    call_msg = {
        "id": 1,
        "type": "call_service",
        "domain": domain,
        "service": service,
        "return_response": return_response
    }
    
    data = service_data or {}
    if entity_id:
        data["entity_id"] = entity_id
    
    if data:
        call_msg["service_data"] = data
    
    ws.send(json.dumps(call_msg))
    result = json.loads(ws.recv())
    ws.close()
    
    return result


if __name__ == "__main__":
    result = call_service("switch", "turn_off", entity_id="switch.plug_a")
    print(f"Turn off: {result['success']}")
    
    result = call_service("light", "turn_on", entity_id="light.kitchen",
                          service_data={"brightness": 128})
    print(f"Turn on: {result['success']}")
    
    result = call_service("switch", "toggle",
                          entity_id=["switch.plug_a", "switch.plug_b"])
    print(f"Toggle: {result['success']}")
