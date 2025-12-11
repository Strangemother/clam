"""
Example usage of the Client.
Customize the perform_work function for your specific needs.
"""

from client import Client
import time


def perform_work(message):
    """
    Custom work logic - modify this function for your use case.
    
    Args:
        message: The message received from the remote caller
        
    Returns:
        The result of processing the message
    """
    # Simulate some work being done
    time.sleep(1)
    
    # Process the message
    result = f"Processed message: {message}"
    
    return result


if __name__ == "__main__":
    # Create and start the client
    client = Client(perform_work)
    client.start()
