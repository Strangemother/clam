"""
Bulby connects LightBulb terminal chat with the call service.

https://www.home-assistant.io/integrations/light/
https://andi-siess.de/rgb-to-color-temperature/
Run:

    (env)> py lightshot.py

tested params:

    (relax, energize, concentrate, reading)
    profile=str
    hs_color=[Hue 0-360, saturation 0-100]
    xy_color=[x,y] #floats
    rgb_color=[r,g,b] #0-255
    rgbw_color=[r,g,b,w] #0-255
    brightness_pct=100,
    color_temp_kelvin=3200
    color_name=red
    brightness= 1 255 #0 == off
    brightness_step=-255 255

When applying color_temp_kelvin, a color value cannot be applied:

    color_temp_kelvin=3200,
    brightness_pct=10,


# not on tapo

    flash='short'
    rgbw_color=[255,255,255, 200]

"""
from clam.terminal_client import TerminalClient, get_prompt_file, Prompt

import sys

other = "C:/Users/jay/Documents/projects/matter-plugs/ha/"
sys.path.append(other)

from call_service import LightBulb

lb = LightBulb(entity_id="light.smart_multicolor_bulb_2")

service_call = lb.make_call("turn_on",
    # rgb_color=[255,255,255],
    # rgbw_color=[255,255,255, 200], # not on tapo
    color_temp_kelvin=3200,
    # brightness_pct=10,
    # brightness_step=-10

    transition=5
)

res = lb.service_call(service_call)