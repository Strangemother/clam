
## Message ID

Every message is given a new ID from the SocketWrapper

## Session ID

When a socket connects, its assigned a single _session id_, allowing persistence of convresation through a single ID.

This session ID is owned by the user - and can be remounted by other sockets.
For example the user can use the same session ID for a mobile device and the desktop at the same time.

## Origin ID

A message into the system is given an origin id. This is similar to both a message and a session ID, for this single _strand_ of work.


When a message is sent into the server, it's given a new message id, and the existing session id. If the origin ID is missing, a new one is applied.
The message propagates through the cluster, with units of work, responding back on the same origin ID.

For example

    session ID ---------------------------------------------...
                Message ID --|-----|--------|--------|
                Origin  ID --------------------------|
                        |
                user => cluster => LM => cluster => user
