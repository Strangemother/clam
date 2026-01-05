
GRAPH = {
    "EchoClient": ["EchoClient"],
    "foo": ["fish"],
    "fish": "egg",
    "egg": ["foo"],
}


def graph_get(client_name, default=None):
    """Get the graph destinations for a given client name."""
    r = GRAPH.get(client_name, default)
    if isinstance(r, str):
        return [r]
    return r
