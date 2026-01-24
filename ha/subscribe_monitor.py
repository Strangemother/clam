"""Similar to subscribe, but with monitoring of distinct events.

"""
import os
from pathlib import Path
from datetime import datetime
import json
from shared import connect_and_auth


HERE = Path(__file__).parent


def main():
    m = Monitor()
    m.run()


class Monitor:
    def connect(self):
        ws = connect_and_auth()
        ws.send(json.dumps({"id": 1, "type": "subscribe_events"}))
        ws.recv()
        print("Listening for events (Ctrl+C to exit)\n")
        self.ws = ws

    def run(self):
        self.connect()
        self.loop()

    def loop(self):
        ws = self.ws
        try:
            while True:
                self.process(ws.recv())
        except KeyboardInterrupt:
            print('Keyboard Interrupt.')
        finally:
            ws.close()

    def save_event(self, msg_dict):
        # safe to cache, under event_id and event_type.
        event = msg_dict["event"]
        event_type = event['event_type']
        data = event.get('data')
        _id = data.get('entity_id') # 'switch.smart_wi_fi_plug_2',

        dts = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
        filename = f'{dts}.json'

        if _id is None:
            _id = data.get('service_data', {}).get('entity_id')
        if _id is None:
            _id = data.get('context', {}).get('id')
        if _id is None:
            _id = event.get('context', {}).get('id')

        cache_dir = Path(HERE) / 'cache' / event_type / _id
        if cache_dir.exists() is False:
            os.makedirs(cache_dir)
        outpath = cache_dir / filename
        outpath.write_text(json.dumps(msg_dict, indent=4))

    def process(self, ws_recv):
        msg = json.loads(ws_recv)
        self.save_event(msg)

        fmap = {
            'light.smart_multicolor_bulb_2': self.state_changed_light_bulb_2
        }

        if msg["type"] == "event":
            event = msg["event"]
            d = event.get('data')
            if d is None:
                print('! no data')
                print(json.dumps(event, indent=2))
            else:
                _id = d.get('entity_id') # 'switch.smart_wi_fi_plug_2',
                if _id is None:
                    print(json.dumps(event, indent=2))
                    print("-" * 50)
                else:
                    print(f"Event: {event['event_type']}", _id)
                    f = fmap.get(_id)
                    if f is not None:
                        f(event)
                # print("-" * 50)
                return
        print('Unknown', msg["type"])

    def state_changed_light_bulb_2(self, event):
        print(json.dumps(event, indent=4))


if __name__ == "__main__":
    main()
