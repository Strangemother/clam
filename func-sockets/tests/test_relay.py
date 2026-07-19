import json

import pytest

from relay import GraphRelay, graph_id_from_path


class FakeSocket:
    def __init__(self) -> None:
        self.messages: list[str | bytes] = []

    async def send(self, message: str | bytes) -> None:
        self.messages.append(message)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/graph/alpha", "alpha"),
        ("/graphs/alpha", "alpha"),
        ("/alpha", "alpha"),
        ("/?graph_id=alpha", "alpha"),
        ("/graph/my%20graph", "my graph"),
        ("/", None),
        ("/unrecognised/alpha", None),
    ],
)
def test_graph_id_from_path(path: str, expected: str | None) -> None:
    assert graph_id_from_path(path) == expected


@pytest.mark.asyncio
async def test_messages_only_reach_peers_in_the_same_graph() -> None:
    relay = GraphRelay()
    graph_source = FakeSocket()
    graph_ui = FakeSocket()
    other_ui = FakeSocket()

    relay.bind(graph_source, "graph-a")
    relay.bind(graph_ui, "graph-a")
    relay.bind(other_ui, "graph-b")

    message = '{"kind":"event","name":"node.output_emitted"}'
    await relay.receive(graph_source, message)

    assert graph_source.messages == []
    assert graph_ui.messages == [message]
    assert other_ui.messages == []


@pytest.mark.asyncio
async def test_bind_message_selects_and_can_change_graph() -> None:
    relay = GraphRelay()
    client = FakeSocket()
    first_peer = FakeSocket()
    second_peer = FakeSocket()
    relay.bind(first_peer, "first")
    relay.bind(second_peer, "second")

    await relay.receive(client, '{"type":"bind","graph_id":"first"}')
    assert json.loads(client.messages.pop()) == {"type": "bound", "graph_id": "first"}

    await relay.receive(client, "first message")
    assert first_peer.messages == ["first message"]
    assert second_peer.messages == []

    await relay.receive(client, '{"type":"bind","graph_id":"second"}')
    assert json.loads(client.messages.pop()) == {"type": "bound", "graph_id": "second"}

    await relay.receive(client, b"second message")
    assert first_peer.messages == ["first message"]
    assert second_peer.messages == [b"second message"]


@pytest.mark.asyncio
async def test_unbound_client_receives_an_error() -> None:
    relay = GraphRelay()
    client = FakeSocket()

    await relay.receive(client, "hello")

    assert json.loads(client.messages[0]) == {
        "type": "error",
        "message": "bind to a graph before sending messages",
    }


@pytest.mark.asyncio
async def test_invalid_bind_is_rejected_as_control_message() -> None:
    relay = GraphRelay()
    client = FakeSocket()
    peer = FakeSocket()
    relay.bind(client, "existing")
    relay.bind(peer, "existing")

    await relay.receive(client, '{"type":"bind","graph_id":null}')

    assert json.loads(client.messages[0]) == {
        "type": "error",
        "message": "graph_id must be a string",
    }
    assert peer.messages == []
