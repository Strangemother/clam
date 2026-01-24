import requests
from pprint import pprint as pp
from _creds import *

entity = "light.smart_multicolor_bulb_2"
url = f"{HA_URL}/api/states/{entity}"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

r = requests.get(url, headers=headers)
r.raise_for_status()

state = r.json()

print("State:", state["state"])
pp(state["attributes"])
