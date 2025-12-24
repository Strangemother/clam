
GRAPH = {
    "EchoClient": ["EchoClient"]
}


def graph_get(client_name, default=None):
    """Get the graph destinations for a given client name."""
    return GRAPH.get(client_name, default)
