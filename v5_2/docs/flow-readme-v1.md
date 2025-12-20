# Client Prototype

Standalone Python clients that communicate with each other via HTTP, simulating async work with responses.

## Quick Start

```bash
pip install -r requirements.txt

# Terminal 1
python client_a.py  # Alice on :8010

# Terminal 2
python client_b.py  # Bob on :8020

# Terminal 3
python client_c.py  # Charlie on :8030
```

## What Happens

**Flow:** Alice → Bob → Charlie → Alice (repeat)

- Alice auto-starts after 3s, sends to Bob
- Charlie auto-starts after 5s, sends to Alice
- Each client responds "thanks" immediately when receiving a message
- After random 2-8s delay, sends work result back to sender
- Then forwards new message to next client in chain

**Output per message:**
1. Receiver prints "Received: [message]" + "Response: thanks"
2. Receiver prints "will perform work: [message]"
3. Sender prints "Got response: okay, I'll do that (says [Name])"
4. Receiver sends next message after delay

## Basic Usage

```python
from client import Client

def perform_work(message):
    # Custom work logic
    return f"Processed: {message}"

client = Client(perform_work, port=8000, name="MyClient")
client.start()
```


## Endpoints

- `GET /` - Client info (name, port)
- `POST /message` - Async message (returns "thanks" immediately)
- `POST /work` - Sync work (waits for result)
- `POST /response` - Receives work results from other clients
- `GET /ping` - Health check

## Architecture

Simple Flask server + threading for non-blocking work. Each client can handle multiple concurrent messages.