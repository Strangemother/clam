"""
Client A - Running on port 8010
"""

from client import Client
import time
import random
from threading import Timer


CLIENT_B_URL = "http://localhost:8020"


def perform_work(message):
    """
    Custom work logic for Client A.
    Wait 2-8 seconds then send a message to Client B.

    Args:
        message: The message received from the remote caller
    """

    def delayed_send():
        client.send_message(CLIENT_B_URL, f"Ping from Alice at {time.time()}")

    print(f"[Alice Client] will perform work: {message}")
    # Schedule message to Client B in 2-8 seconds (random)
    delay = random.uniform(2, 8)
    timer = Timer(delay, delayed_send)
    timer.daemon = True
    timer.start()
    return "okay, I'll do that (says Alice)"


def start_process():
    """Initiate the first message to Client B."""
    print(f"[Alice Client] Starting ping-pong process...")
    client.send_message(CLIENT_B_URL, f"Initial ping from Alice at {time.time()}")


if __name__ == "__main__":
    # Create Client A with auto-start after 3 seconds
    client = Client(perform_work, port=8010, name="Alice Client", auto_start=3, on_start=start_process)
    client.start()
