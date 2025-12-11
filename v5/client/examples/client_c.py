"""
Client C - Running on port 8030
"""

from client import Client
import time
import random
from threading import Timer
from jinja2 import Template
import os


CLIENT_A_URL = "http://localhost:8010"

# Load template
template_path = os.path.join(os.path.dirname(__file__), 'templates/client_c.txt')
with open(template_path, 'r') as f:
    RESPONSE_TEMPLATE = Template(f.read())


def perform_work(message):
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
        client_name="Charlie Client",
        port=8030
    )
    
    return response


def start_process():
    """Initiate the first message to Client A."""
    print(f"[Charlie Client] Starting ping-pong process...")
    client.send_message(CLIENT_A_URL, f"Initial ping from Charlie at {time.time()}")


if __name__ == "__main__":
    # Create Client C with auto-start after 5 seconds (staggered from Alice)
    client = Client(perform_work, port=8030, name="Charlie Client", auto_start=5, on_start=start_process)
    client.start()
