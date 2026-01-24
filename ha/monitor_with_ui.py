"""Monitor with WebSocket UI broadcasting."""
import asyncio
import threading
import json
import time
from ws_server import broadcast, start_server, CLIENTS

# Set to True to test UI without Home Assistant connection
MOCK_MODE = True


class MonitorWithUI:
    def __init__(self):
        self.loop = None
        self.ws = None

    def start_ws_server(self):
        """Run WebSocket server in a separate thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(start_server())

    def run(self):
        # Start WebSocket server in background thread
        ws_thread = threading.Thread(target=self.start_ws_server, daemon=True)
        ws_thread.start()
        print("Open ha/index.html in browser to view events")
        
        if MOCK_MODE:
            self.mock_loop()
        else:
            from subscribe_monitor import Monitor
            self.connect = Monitor.connect.__get__(self, MonitorWithUI)
            self.connect()
            self.loop_with_broadcast()

    def loop_with_broadcast(self):
        ws = self.ws
        try:
            while True:
                data = ws.recv()
                msg_dict = json.loads(data)
                self.broadcast_to_ui(msg_dict)
        except KeyboardInterrupt:
            print('Keyboard Interrupt.')
        finally:
            ws.close()

    def mock_loop(self):
        """Send fake events for testing the UI."""
        import random
        entities = ['light.living_room', 'switch.plug_1', 'sensor.temperature', 'binary_sensor.motion']
        try:
            while True:
                time.sleep(2)
                mock_event = {
                    "type": "event",
                    "event": {
                        "event_type": "state_changed",
                        "data": {
                            "entity_id": random.choice(entities),
                            "new_state": {"state": random.choice(["on", "off"])}
                        }
                    }
                }
                print(f"Mock: {mock_event['event']['data']['entity_id']}")
                self.broadcast_to_ui(mock_event)
        except KeyboardInterrupt:
            print('Keyboard Interrupt.')

    def broadcast_to_ui(self, msg_dict):
        if self.loop and CLIENTS:
            asyncio.run_coroutine_threadsafe(broadcast(msg_dict), self.loop)


if __name__ == "__main__":
    m = MonitorWithUI()
    m.run()
