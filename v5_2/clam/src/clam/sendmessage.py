"""
Memorybpt - Running on port 9383
"""

from client import Client
import time
import random
from threading import Timer
from jinja2 import Template
import os

MY_PORT = 9383
CLIENT_A_URL = "http://localhost:8010"


# Load template
template_path = os.path.join(os.path.dirname(__file__), 'templates/memorybot.txt')
with open(template_path, 'r') as f:
    RESPONSE_TEMPLATE = Template(f.read())



def main():
    # Create Client C with auto-start after 5 seconds (staggered from Alice)
    client = Client(start_process,
                    port=MY_PORT,
                    name="memorybot",
                    # auto_start=5,
                    # on_start=start_process
                )
    client.send_message(CLIENT_A_URL, f"Hello from script")
    # client.start()


def start_process():
    """Initiate the first message to Client A."""
    print(f"[Charlie Client] Starting ping-pong process...")


if __name__ == "__main__":
    main()
