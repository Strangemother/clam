"""
Simple test script to send messages to the running client.
Run this in a separate terminal while the client is running.
"""

import requests
import json


def test_sync_work():
    """Test the synchronous /work endpoint."""
    url = "http://localhost:8000/work"
    payload = {"message": "Hello from test!"}
    
    print(f"Sending to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_async_message():
    """Test the asynchronous /message endpoint."""
    url = "http://localhost:8000/message"
    payload = {"message": "Async message from test!"}
    
    print(f"Sending to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_ping():
    """Test the health check endpoint."""
    url = "http://localhost:8000/ping"
    
    print(f"Pinging {url}...")
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


if __name__ == "__main__":
    print("Testing client endpoints...\n")
    
    try:
        test_ping()
        test_sync_work()
        test_async_message()
        print("All tests completed!")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to client. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"Error: {e}")
