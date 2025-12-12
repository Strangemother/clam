"""
Memorybpt - Running on port 9383
"""

import os
import time
import json
import random
import pathlib
from threading import Timer

from jinja2 import Template

from client import Client
from bot_pipe import send_wait, print_content_response, print_payload_messages


NAME = 'memorybot'
CACHE_DIR = pathlib.Path(f'./cache/{NAME}/')
TEMPLATE = f'templates/{NAME}.txt'

MY_PORT = 9383
CLIENT_A_URL = "http://localhost:8010"



# Load template
template_path = os.path.join(os.path.dirname(__file__), TEMPLATE)

def get_template():
    with open(template_path, 'r') as f:
        return Template(f.read())


RESPONSE_TEMPLATE = get_template()


def save_raw(d):
    filename = f"raw/{d['id']}-{d['created']}.json"
    p = as_cache_path(filename)
    p.write_text(json.dumps(d, indent=4))


def main():
    client = Client(perform_work,
                    port=MY_PORT,
                    name=NAME,
                    # auto_start=5,
                    # on_start=start_process
                )
    client.start()


def save_memory(d):
    """Create a neater memory, for future callback as inline memory content text
    """
    text = easy_extract_message(d)
    if text:
        filename = f"memory/{d['id']}-{d['created']}.txt"
        p = as_cache_path(filename)
        p.write_text(text)
        print("memory saved: ", p)
        return
    print('No memory for this')
    return


def as_cache_path(filename):
    """Save to the correct place.
    """
    return CACHE_DIR / filename


def easy_extract_message(d):
    return d['choices'][0]['message']['content']


def get_rendered_template_message(message):

    # Render template response
    response = get_template().render(
        message=message,
        timestamp=time.time(),
        process_id=random.randint(1000, 9999),
        client_name=NAME,
        port=MY_PORT
    )

    return response


def perform_work(message):
    """Memory sends a message to the llm, templated through the text file.
    The response is saved an a messsage is sent back to
    """
    print('WORK: make memory')
    # Make LLM request with templated message.
    vv = get_rendered_template_message(message)
    # vv = 'Favourite color?'
    print("sending:", vv)
    d = send_wait(vv)
    # print("d", d)
    print_content_response(d)
    save_raw(d)
    save_memory(d)



def example_perform_work(message):
    """
    Custom work logic for Client C.
    Wait 2-8 seconds then send a message to Client A.
    Uses Jinja2 template for response.

    Args:
        message: The message received from the remote caller
    """
    def delayed_send():
        client.send_message(CLIENT_A_URL, f"Ping from Charlie at {time.time()}")

    print(f"[Charlie Client] will perform work: {message}")

    # Schedule message to Client A in 2-8 seconds (random)
    delay = random.uniform(2, 8)
    timer = Timer(delay, delayed_send)
    timer.daemon = True
    timer.start()

    # Render template response
    response = RESPONSE_TEMPLATE.render(
        message=message,
        timestamp=time.time(),
        process_id=random.randint(1000, 9999),
        client_name="memorybot",
        port=MY_PORT
    )

    return response


def start_process():
    """Initiate the first message to Client A."""
    print(f"[Charlie Client] Starting ping-pong process...")
    client.send_message(CLIENT_A_URL, f"Initial ping from Charlie at {time.time()}")


if __name__ == "__main__":
    main()
