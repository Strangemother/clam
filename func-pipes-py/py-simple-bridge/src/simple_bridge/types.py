from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class PipRef:
    """Reference one concrete pip on one node.

    Description:
        Store the node id and pip name together so connections and queued
        events can point to a specific endpoint.

    Example:
        pip = PipRef("node_a", "foo")
        key = pip.key

    Expected output:
        `key` is `"node_a:foo"`.

    Caveats:
        The default pip name is `in`, but any string is valid.
    """

    node_id: str
    pip: str = "in"

    @classmethod
    def from_value(
        cls,
        value: PipRef | Mapping[str, str] | tuple[str, str] | str,
        default_pip: str = "in",
    ) -> PipRef:
        """Normalize several pip reference shapes into a `PipRef`.

        Description:
            Accept an existing `PipRef`, a mapping, a `(node_id, pip)` tuple,
            or a bare node id string and convert it into one immutable object.

        Example:
            pip = PipRef.from_value({"id": "node_b", "pip": "bar"})

        Expected output:
            `pip` becomes `PipRef(node_id="node_b", pip="bar")`.

        Caveats:
            A bare string uses `default_pip`, and mappings must include `id`
            or `node_id`.
        """
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            return cls(node_id=value, pip=default_pip)

        if isinstance(value, tuple):
            node_id, pip = value
            return cls(node_id=node_id, pip=pip)

        node_id = value.get("node_id") or value.get("id")
        if node_id is None:
            raise ValueError("Pip references require an 'id' or 'node_id'.")

        pip = value.get("pip", default_pip)
        return cls(node_id=str(node_id), pip=str(pip))

    @property
    def key(self) -> str:
        """Build the registry key used by the bridge stores.

        Description:
            Join the node id and pip name into one stable lookup string.

        Example:
            PipRef("node_c", "baz").key

        Expected output:
            Returns `"node_c:baz"`.

        Caveats:
            The bridge treats this as a plain string key, so uniqueness depends
            on your node ids and pip names.
        """
        return f"{self.node_id}:{self.pip}"


@dataclass(frozen=True, slots=True)
class Edge:
    """Represent one directed connection between two pips.

    Description:
        Store the source pip, destination pip, and optional metadata for one
        bridge connection.

    Example:
        edge = Edge(PipRef("node_a", "foo"), PipRef("node_b", "bar"))

    Expected output:
        `edge.from_node` points at `node_a:foo` and `edge.to_node` points at
        `node_b:bar`.

    Caveats:
        The bridge does not interpret `meta`; it is stored for callers.
    """

    from_node: PipRef
    to_node: PipRef
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BridgeEvent:
    """Hold one queued event for the bridge loop.

    Description:
        Carry an event type and payload through the waiting queue until the
        bridge dispatches it.

    Example:
        event = BridgeEvent("demo:start", {"value": 3})

    Expected output:
        `event.event_type` is `"demo:start"` and `event.payload` contains the
        supplied data.

    Caveats:
        The payload is mutable, so callers should avoid sharing a dict that may
        be modified elsewhere.
    """

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NodeOutput:
    """Describe an explicit outbound emission from a node.

    Description:
        Let a node return both a value and the exact outbound pip name that the
        bridge should route from.

    Example:
        output = NodeOutput(value="seed:entry", pip="foo")

    Expected output:
        The bridge will emit a `bridge:node_result` event from `foo` instead of
        the default `out` pip.

    Caveats:
        Returning a plain value still routes through `out`; use `NodeOutput`
        only when you need to override the outbound pip.
    """

    value: Any
    pip: str = "out"


@runtime_checkable
class GraphNode(Protocol):
    """Describe the minimum node interface the bridge can execute.

    Description:
        Define the shape required for any object registered with the bridge:
        a `node_id` and a `graph_execute()` method.

    Example:
        class MyNode:
            node_id = "node_a"

            async def graph_execute(self, value, pip="in"):
                return value

    Expected output:
        Objects matching this protocol can be passed to
        `SimpleBridge.register_node()`.

    Caveats:
        The bridge checks behavior at runtime when the node is called; protocol
        compliance is mostly a typing aid.
    """

    node_id: str

    def graph_execute(self, value: Any, pip: str = "in") -> Any:
        """Execute one node call for one input value and pip.

        Description:
            Accept the incoming value and pip name, then return either a plain
            result or a `NodeOutput` for named outbound routing.

        Example:
            async def graph_execute(self, value, pip="entry"):
                return NodeOutput(value=value, pip="foo")

        Expected output:
            The bridge receives a value to emit, or a `NodeOutput` that names
            the outbound pip explicitly.

        Caveats:
            Exceptions raised here are converted into `bridge:node_error`
            events by the bridge.
        """
