# Home Assistant WebSocket Tools

Simple Python scripts for controlling Home Assistant via WebSocket.

## Installation

```bash
pip install websocket-client
```

## Setup

1. **Get your access token** from Home Assistant:
   - Go to your Home Assistant profile (click your name in sidebar)
   - Scroll to "Long-Lived Access Tokens"
   - Click "Create Token"
   - Copy the token

2. **Update credentials** in `_creds.py`:
   ```python
   WS_URL = "ws://homeassistant.local:8123/api/websocket"
   ACCESS_TOKEN = "your_token_here"
   ```

## Usage

**Call a service:**
```bash
python call_service.py
```

**Use the helper function:**
```bash
python service_helper.py
```

**Subscribe to events:**
```bash
python subscribe_simple.py
```

## Quick Examples

```python
from service_helper import call_service

# Turn off a switch
call_service("switch", "turn_off", entity_id="switch.plug_a")

# Turn on a light with brightness
call_service("light", "turn_on", entity_id="light.kitchen", 
             service_data={"brightness": 128})

# Toggle multiple switches
call_service("switch", "toggle", 
             entity_id=["switch.plug_a", "switch.plug_b"])
```

That's it.
