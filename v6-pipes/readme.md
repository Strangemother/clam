# Pipes

Extending from _ALL_ the versions found in graph-pipes-old, this is a cleaner version focusing on:

+ Python loop
+ json definition
    + node
    + pips
    + content
+ python node definition
    + nodes
    + connections
    + executable code
    + can be loaded by json
+ graph definition
+ websocket connections

The backend is a websocket server with a concurrent execution graph. Through the socket or a endpoint, 

+ create/destroy a graph
+ push events
+ receive events
    + live through sockets
    + queued through http


The functionality is as pure as it can be:

1. node emits event (through a pip)
2. node receives an event (through a pip)

The graph manages the event flow.

    > socket connect
    > {event:foo}

## stepping

The _stepping_ of the events occurs through the background loop. This can be managed through a command.