"""This files serves as a config for the _client_ settings when it wakes.
this functionality dictates how the client should be onboarded to the cluster,
and act when messaged.

Fundamentally we provide a _name_ and abilities. E.g. if this is a memory
module, it receives _secondary layer_ messages. If it is a preliminary
decision layer, it'll accept messages from the _user_ sending the next messages
to the thinking units.

However that decision mapping is done in the cluster, this serves as a simple
identity, The functionality is abstract from the cluster.

This could have been a JSON file, but py files allow comments by default.
"""

role = 'alpha'

abilities = ['text']