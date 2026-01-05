"""Post some work to a client.

    post.py --port 60385

With the bat:

    run_abs.bat post.py light.turn_on --port 60385

The message is send also send to the backbone.
"""
import requests


import argparse

parser = argparse.ArgumentParser(description="Clam Post")
parser.add_argument('--port', default=9202, type=int)
parser.add_argument('text', default='I like butterscotch', type=str)

ns, unknown = parser.parse_known_args()

url = f'http://127.0.0.1:{ns.port}/job'

res = requests.post(url,
        data=bytes(ns.text, 'utf'),
        timeout=3,
        # headers=headers
    )


print(res.text)