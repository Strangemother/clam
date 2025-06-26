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

# Define the tooling slot type, such as "memory" or "user"
# sent to the cluster on client_connected.
ROLE = 'example'

from file_text import file_text

# The instruction message.
FIRST_MESSAGE =  {
    "role": "system",
    # "content": file_text('./angrybot-prompt.txt'),
    "content": file_text('./kettle-prompt.txt'),
    # "content": file_text('./moly-prompt.txt'),
}

# Custom locked ID for this client - may be a forced key by the cluster.
UUID = 1000

abilities = ['text']

# The cluster endpoint
WEBSOCKET_ENDPOINT = "ws://localhost:8765"

# The service endpoint - in this case, basic olloma.
OLLOMA_CHAT_ENDPOINT = "http://192.168.50.60:10000/api/chat/"

# The model selected on the service. Examples
# TinyDolphin
# llama3.2:latest
# "gemma-2-2b-it-abliterated-Q8_0-1750821090814:latest"
#  'smollm2:360m-instruct-fp16'
MODEL_NAME = "gemma-2-2b-it-abliterated-Q8_0-1750821090814:latest"
