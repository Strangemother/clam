# Version 2

This is the version 2 of this client. It's task:

1. Be a self-contained _proxy_ to the target LLM
2. The target llm is the API of any type.
    Such as vLLM, Olloma, LM Studio, Gradio etc.
3. The unit runs as a tool for the target (normalised)
4. An a prepared API for the primary.

# self contained

It can access its target llm through its own tooling, and have a minor interface
to use that tool. This same minor tool is applied to the users UI as a slotted app (e.g. gradio settings)

Therefore doubles as a stand-alone UI and a chat widget.

# Normalised Target LLM

Any LLM from any Tool. Each tool has a unique interface, therefore messages are _corrected_ in this client, before bounding to the llm and back to the user.

The target is unaware _this client_ is the caller. The _primary_ is unaware of the model or tooling behind this client.

Fundamentally like a proxy

---

For this, the _this client_ is configured by the primary; or within the clients own settings panel (exposing the same settings.)

It communicates to the primary through socket and http
z