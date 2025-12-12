"""
Client B - Running on port 8020
"""

from client import Client
import time
import random
from threading import Timer


CLIENT_C_URL = "http://localhost:8030"


def perform_work(message):
    """
    Custom work logic for Client B.
    Wait 2-8 seconds then send a message to Client C.
    
    Args:
        message: The message received from the remote caller
    """
    def delayed_send():
        client.send_message(CLIENT_C_URL, f"Pong from Bob at {time.time()}")
    
    print(f"[Bob Client] will perform work: {message}")
    # Schedule message to Client C in 2-8 seconds (random)
    delay = random.uniform(2, 8)
    timer = Timer(delay, delayed_send)
    timer.daemon = True
    timer.start()


if __name__ == "__main__":
    # Create Client B (no auto-start, waits for Client A)
    client = Client(perform_work, port=8020, name="Bob Client")
    client.start()
