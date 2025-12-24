
A Client can:

- Register as a client
- send requests to the Orchestra server
- receive responses from the Orchestra server

A Server can:

- receive requests from Clients
- process requests
- send responses back to Clients

---

Key Features:

- push anything (json, bytes, socket streams)
- http post/get requests for clients 
- websocket support for clients 

---

Routing:

- A client sends a message, a receives a receipt.
- The server routes work. The destination client receives the message and sends a receipt.
- The client works and sends a response back to the receipt address (happens to be the server).
- The server routes the response back to the original receipt address (the client).
- The client receives the receipt response, and continues processing.

This is all done through http/websocket connections.

---

The client does not need to be aware of the server, or other clients - just _receipts_ and responses.
A client just receives "I got a job, response to this address when done".

---

The server simply receives _posts_ or _gets_ etc as events. and routes them to the dest client in the message.
If no dest client is in the data, the server uses the graph.

The server receives a message, and routes it to the dest client. It receives a receipt and expects a response back to the receipt address.
The client simply responds to the receipt address when done.

---

In the future, the server could:

- server to server allowing distributed orchestration
- allow peer to peer routing
- allow more complex graph routing
- allow more complex orchestration (workflows, etc)

But for now, this is a simple orchestration server is powerful enough.

---

Uses:

Any client can _throw_ a message to a server. We register a _thing_ with a name

---

## Info

Consider this a no-nonsense, minimalistic implementation of a graph-based orchestration server. A client pushes a http message (likely json). This includes the name, destination, and data. The server pushes the message to the destination client through the graph connection. 

The purpose is a no-config "hop on/off" network for private clients to communicate through a central server.
The event content should be completely opaque to the server. The server just routes messages.

### Client Flow

1. registers with the server (http post)
2. waits for a response from the server (http get/websocket)
3. On receive send a receipt,
4. processes the response and send to receipt address (http post)
5. waits for a response from the server (http get/websocket)

#### Registration

The client registers with the server:

```
POST /register
{
  "name": "client_name",
  "address": "http://client_address:port/receive",
  "anything_else": "..."
}
```

With the python library:

```python
from orchestra import backbone

backbone.register(
    name="client_name",
    address="http://client_address:port/receive",
    anything_else="..."
)
```

This is ready and waiting for messages.

#### Receiving Messages

When a message is received, the client sends a receipt back to the server:

```json
POST /receive 

```

returns:

```json
{
    "status": "received",
    "receipt_id": "12345"
}
```

In this case the _from_ and _to_ are the server, as the server is routing messages.

#### Sending Responses

The client processes the data, and when done, sends the response to the receipt address:

```py
# POST http://orchestra_server:port/postback/{receipt_id}
{
    ... # the result of processing
}
```

No nonsense; just send the result to the receipt address.

#### Sending Messages

A client can send messages to other clients through the server.
This is designed to be as simple and transparent as possible.

1. Make a request to the server `POST /dispatch/[client_name]`
2. Put the data in the body

Your data can be anything. Your receiver should know what to do with it.

### Server Flow

1. receives a message from a client (http post)
2. routes the message to the destination client (http post)
3. receives a receipt from the destination client (http post)
4. waits for a response from the destination client (http post)
5. routes the response back to the original client (http post)

