"""
Bulby connects LightBulb terminal chat with the call service.

https://www.home-assistant.io/integrations/light/

Run:

    (env)> py bulbly.py

tested params:

    (relax, energize, concentrate, reading)
    profile=str
    hs_color=[Hue 0-360, saturation 0-100]
    xy_color=[x,y] #floats
    rgb_color=[r,g,b] #0-255
    rgbw_color=[r,g,b,w] #0-255
"""
from clam.terminal_client import TerminalClient, get_prompt_file, Prompt

import sys

other = "C:/Users/jay/Documents/projects/matter-plugs/ha/"
sys.path.append(other)

from call_service import LightBulb


class BulblyTerminalClient(TerminalClient):

    def store_response(self, data, resp):
        resp = super().store_response(data, resp)
        # send to speaker.
        d = self.get_response_message(resp)
        self.read_answer(d)
        return resp

    def read_answer(self, d):
        print('Bulb', d)
        actionmap = {
            'no_change': self.no_change,
            'off': self.off,
        }

        try:
            a, b = d.split(' ')
            # lb.perform(args.service)
            # service_call = lb.make_call("turn_on", hs_color=[233.2,90.1])
            # service_call = lb.make_call("turn_on", color_name='red')
            rgb = hex_to_rgb(a[1:])
            if sum(rgb) == 0:
                self.off()
                return
            self.change_rgb(rgb, int(b))

        except ValueError:
            # must be something else.
            f = actionmap.get(d.lower(), None)
            if f:
                return f(d)
            print('Error with value.')

    def get_bulb(self):
        return LightBulb(entity_id="light.smart_multicolor_bulb_2")

    def off(self):
        lb = self.get_bulb()
        lb.off()

    def no_change(self, d):
        print('No change.')

    def change_rgb(self, rgb, brightness_pct=None):
        lb = self.get_bulb()
        # service_call = lb.make_call("turn_on", profile='relax')
        # service_call = lb.make_call("turn_on", hs_color=[100.2,100.0])
        kw = {
            'rgb_color': rgb
        }

        if brightness_pct is not None:
            kw['brightness_pct'] = brightness_pct

        service_call = lb.make_call("turn_on", **kw)#, brightness_pct=90)
        # service_call = lb.make_call("turn_on", rgb_color=rgb, brightness_pct=90)
        print(service_call)
        res = lb.service_call(service_call)
        # service_call = lb.make_call("turn_on", rgb_color=[r, b, g])
        # lb.perform(args.service)


def hex_to_rgb(hexa):
    # Source - https://stackoverflow.com/a/71804445
    return tuple(int(hexa[i:i+2], 16)  for i in (0, 2, 4))


def main():
    """The user (termnial input) communicates directly to the model,
    using the loaded prompt as the system message.
    """
    pf = f'prompts/rgb-light.prompt.md'
    # pf = f'prompts/rgb.prompt.md'
    pr = Prompt(pf)
    tc = BulblyTerminalClient(pr)

    return tc.loop()


if __name__ == '__main__':
    main()