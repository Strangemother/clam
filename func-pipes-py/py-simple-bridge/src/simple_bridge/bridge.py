from __future__ import annotations

import asyncio
import inspect
from collections import deque
from typing import Any, Iterable, Mapping

from .events import EventEmitter
from .types import BridgeEvent, Edge, GraphNode, NodeOutput, PipRef


class SimpleBridge:
    """Route queued events and node calls through a small graph.

    Description:
        Own node registration, pip connections, event subscriptions, and the
        waiting queue that powers the bridge execution loop.

    Example:
        bridge = SimpleBridge()
        bridge.connect_pips(("node_a", "foo"), ("node_b", "bar"))

    Expected output:
        The bridge can queue a call to `node_a` and propagate results through
        the registered connection graph.

    Caveats:
        Plain node return values emit through `out`; use `NodeOutput` when a
        node must emit on a named outbound pip.
    """

    CALL_NODE = "bridge:call_node"
    NODE_RESULT = "bridge:node_result"
    NODE_ERROR = "bridge:node_error"

    def __init__(self, nodes: Mapping[str, GraphNode] | None = None) -> None:
        """Create a bridge with empty registries and queue state.

        Description:
            Initialize the node registry, connection stores, event bus, and the
            waiting queue used by manual or background execution.

        Example:
            bridge = SimpleBridge()

        Expected output:
            `bridge.waiting_count` starts at `0` and no nodes or edges are
            registered yet.

        Caveats:
            Any nodes passed in must already satisfy the `GraphNode` protocol.
        """
        self.nodes: dict[str, GraphNode] = dict(nodes or {})
        self.edges_registry: dict[str, Edge] = {}
        self.pip_registry: dict[str, dict[str, list[PipRef]]] = {}
        self.event_bus = EventEmitter()
        self.event_log: list[BridgeEvent] = []
        self._waiting_events: deque[BridgeEvent] = deque()
        self._runner_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def waiting_count(self) -> int:
        """Return the number of queued events waiting to run.

        Description:
            Expose the current queue length for diagnostics and tests.

        Example:
            bridge.push_event("demo:start")
            count = bridge.waiting_count

        Expected output:
            `count` increases as events are queued and falls as they are
            processed.

        Caveats:
            This counts only queued events, not work already being executed.
        """
        return len(self._waiting_events)

    @property
    def events(self) -> list[BridgeEvent]:
        """Return a snapshot of the waiting event queue.

        Description:
            Copy the queued events into a new list so callers can inspect the
            pending work without mutating the deque directly.

        Example:
            bridge.push_event("demo:start")
            pending = bridge.events

        Expected output:
            `pending` is a list containing the queued `BridgeEvent` objects.

        Caveats:
            The list is a copy, but the contained event objects are the same
            instances stored in the queue.
        """
        return list(self._waiting_events)

    def on(self, event_type: str, callback):
        """Register a callback for one event type.

        Description:
            Forward a typed subscription request to the bridge event bus.

        Example:
            def handle(event):
                print(event.event_type)

            unsubscribe = bridge.on(SimpleBridge.NODE_RESULT, handle)

        Expected output:
            Returns an `unsubscribe()` callback.

        Caveats:
            Listener failures are logged during emission instead of propagating
            back to the caller.
        """
        return self.event_bus.on(event_type, callback)

    def on_any(self, callback):
        """Register a callback for every bridge event.

        Description:
            Forward a global subscription request to the bridge event bus.

        Example:
            def log_event(event):
                print(event.event_type)

            unsubscribe = bridge.on_any(log_event)

        Expected output:
            The callback runs for all emitted bridge events.

        Caveats:
            Global listeners can become noisy in large graphs.
        """
        return self.event_bus.on_any(callback)

    def register_node(self, node: GraphNode, node_id: str | None = None) -> GraphNode:
        """Add or replace one node in the bridge registry.

        Description:
            Store a node under its own `node_id` or an explicitly supplied id so
            later queued calls can resolve it.

        Example:
            node = FunctionNode("echo", node_passthrough)
            bridge.register_node(node)

        Expected output:
            Returns the same node instance after registering it.

        Caveats:
            Registering a second node with the same id replaces the earlier one.
        """
        resolved_id = node_id or getattr(node, "node_id", None)
        if not resolved_id:
            raise ValueError("Nodes require an explicit node_id.")

        self.nodes[resolved_id] = node
        return node

    def push_event(
        self,
        event: BridgeEvent | str,
        payload: Mapping[str, Any] | None = None,
    ) -> BridgeEvent:
        """Queue one event without processing it yet.

        Description:
            Accept either a ready-made `BridgeEvent` or an event type plus
            payload, then append it to the waiting queue.

        Example:
            event = bridge.push_event("demo:start", {"value": 3})

        Expected output:
            Returns the queued `BridgeEvent` instance.

        Caveats:
            Nothing happens until `call_waiting_events()` or `start()` drains
            the queue.
        """
        if isinstance(event, BridgeEvent):
            queued = event
        else:
            queued = BridgeEvent(event_type=event, payload=dict(payload or {}))

        self._waiting_events.append(queued)
        return queued

    def emit(
        self,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
    ) -> BridgeEvent:
        """Alias `push_event()` for event-style code.

        Description:
            Queue an event using terminology closer to pub/sub APIs.

        Example:
            bridge.emit("demo:start", {"value": 3})

        Expected output:
            Returns the queued `BridgeEvent`.

        Caveats:
            This does not immediately notify listeners; it only queues work.
        """
        return self.push_event(event_type, payload)

    def enqueue_node_call(
        self,
        node: PipRef | Mapping[str, str] | tuple[str, str] | str,
        value: Any,
        pip: str = "in",
    ) -> BridgeEvent:
        """Queue one node invocation for later processing.

        Description:
            Normalize the target node and pip, then enqueue a
            `bridge:call_node` event carrying the input value.

        Example:
            bridge.enqueue_node_call(("node_a", "entry"), "seed")

        Expected output:
            A `BridgeEvent` of type `bridge:call_node` is added to the queue.

        Caveats:
            Missing nodes are not detected here; they become `bridge:node_error`
            events when the queue is processed.
        """
        target = PipRef.from_value(node, default_pip=pip)
        return self.push_event(
            self.CALL_NODE,
            {
                "node": target,
                "value": value,
            },
        )

    def call_node_evented(
        self,
        node: PipRef | Mapping[str, str] | tuple[str, str] | str,
        value: Any,
        pip: str = "in",
    ) -> BridgeEvent:
        """Compatibility wrapper around `enqueue_node_call()`.

        Description:
            Provide a name that mirrors the earlier JavaScript bridge API while
            using the same queueing behavior as `enqueue_node_call()`.

        Example:
            bridge.call_node_evented("node_a", "seed")

        Expected output:
            Returns the same `BridgeEvent` shape as `enqueue_node_call()`.

        Caveats:
            This is just an alias; it does not add extra behavior.
        """
        return self.enqueue_node_call(node=node, value=value, pip=pip)

    def call_nodes_evented(self, nodes: Iterable[PipRef], value: Any) -> None:
        """Queue the same value for several downstream pips.

        Description:
            Iterate over multiple `PipRef` targets and enqueue one node call for
            each of them in order.

        Example:
            bridge.call_nodes_evented([PipRef("a", "foo"), PipRef("b", "bar")], 3)

        Expected output:
            Each target receives its own queued `bridge:call_node` event.

        Caveats:
            Order is preserved from the iterable you pass in.
        """
        for node in nodes:
            self.enqueue_node_call(node=node, value=value, pip=node.pip)

    def emit_result(
        self,
        value: Any,
        origin_node: PipRef | Mapping[str, str] | tuple[str, str] | str,
        pip: str = "out",
    ) -> BridgeEvent:
        """Queue one node-result event from a chosen outbound pip.

        Description:
            Normalize the origin node reference and enqueue a
            `bridge:node_result` event carrying the output value.

        Example:
            bridge.emit_result("done", ("node_a", "foo"), pip="foo")

        Expected output:
            The queued result event reports `node_a:foo` as its origin.

        Caveats:
            Plain node returns usually flow through `out`; use `NodeOutput` to
            request another outbound pip during execution.
        """
        origin = PipRef.from_value(origin_node, default_pip=pip)
        outbound = PipRef(node_id=origin.node_id, pip=pip)
        return self.push_event(
            self.NODE_RESULT,
            {
                "node": outbound,
                "value": value,
            },
        )

    def easy_connect_pips(
        self,
        from_id: str,
        to_id: str,
        meta: Mapping[str, Any] | None = None,
    ) -> Edge:
        """Connect one node's default `out` pip to another node's default `in`.

        Description:
            Provide a short form for the common `out -> in` connection pattern.

        Example:
            bridge.easy_connect_pips("node_a", "node_b")

        Expected output:
            Returns the created `Edge` between `node_a:out` and `node_b:in`.

        Caveats:
            Use `connect_pips()` when either side uses a custom pip name.
        """
        return self.connect_pips(
            PipRef(node_id=from_id, pip="out"),
            PipRef(node_id=to_id, pip="in"),
            meta=meta,
        )

    def connect_pips(
        self,
        from_node: PipRef | Mapping[str, str] | tuple[str, str] | str,
        to_node: PipRef | Mapping[str, str] | tuple[str, str] | str,
        meta: Mapping[str, Any] | None = None,
    ) -> Edge:
        """Connect any source pip to any destination pip.

        Description:
            Normalize both endpoints, create an `Edge`, and update the forward
            and reverse pip registries used by routing.

        Example:
            edge = bridge.connect_pips(("node_a", "foo"), ("node_b", "bar"))

        Expected output:
            `edge` describes the connection, and later routing can move results
            from `node_a:foo` to `node_b:bar`.

        Caveats:
            Reconnecting the exact same pair replaces the stored edge metadata
            in `edges_registry`.
        """
        source = PipRef.from_value(from_node, default_pip="out")
        target = PipRef.from_value(to_node, default_pip="in")
        edge = Edge(from_node=source, to_node=target, meta=dict(meta or {}))

        self.edges_registry[f"{source.key}-{target.key}"] = edge

        source_entry = self.pip_registry.setdefault(source.key, {"to": [], "from": []})
        target_entry = self.pip_registry.setdefault(target.key, {"to": [], "from": []})

        if target not in source_entry["to"]:
            source_entry["to"].append(target)

        if source not in target_entry["from"]:
            target_entry["from"].append(source)

        return edge

    def get_next(
        self,
        from_node: PipRef | Mapping[str, str] | tuple[str, str] | str,
    ) -> list[PipRef]:
        """Return the downstream targets connected to one source pip.

        Description:
            Look up the registered `to` targets for a source node and pip.

        Example:
            next_nodes = bridge.get_next(("node_a", "foo"))

        Expected output:
            Returns a list of `PipRef` objects such as
            `[PipRef("node_b", "bar")]`.

        Caveats:
            Missing connections return an empty list.
        """
        source = PipRef.from_value(from_node, default_pip="out")
        source_entry = self.pip_registry.get(source.key, {})
        return list(source_entry.get("to", []))

    async def call_waiting_events(self, max_events: int | None = None) -> int:
        """Drain queued events until the queue is empty or capped.

        Description:
            Pop events from the waiting queue, notify listeners, run bridge
            dispatch, and count how many events were processed in this cycle.

        Example:
            processed = await bridge.call_waiting_events()

        Expected output:
            `processed` is the number of events handled in that pump cycle.

        Caveats:
            Events queued during dispatch are processed in the same loop unless
            `max_events` stops the pump early.
        """
        processed = 0
        while self._waiting_events:
            if max_events is not None and processed >= max_events:
                break

            event = self._waiting_events.popleft()
            self.event_log.append(event)
            await self.event_bus.emit(event)
            await self._dispatch_event(event)
            processed += 1

        return processed

    async def start(self, interval: float = 0.05) -> asyncio.Task[None]:
        """Start the background queue pump.

        Description:
            Launch an asyncio task that repeatedly drains queued events and then
            sleeps for the requested interval.

        Example:
            task = await bridge.start(interval=0.01)

        Expected output:
            Returns the running asyncio task.

        Caveats:
            Calling `start()` again while the loop is already running returns
            the same task instead of creating a second loop.
        """
        if self._runner_task and not self._runner_task.done():
            return self._runner_task

        self._running = True
        self._runner_task = asyncio.create_task(self._run_loop(interval))
        return self._runner_task

    async def stop(self) -> None:
        """Stop the background queue pump.

        Description:
            Clear the running flag and wait for the active background task to
            exit cleanly.

        Example:
            await bridge.stop()

        Expected output:
            The background loop ends and `_runner_task` is reset to `None`.

        Caveats:
            Stop waits for the current pump or sleep cycle to finish.
        """
        self._running = False

        task = self._runner_task
        if task is None:
            return

        await task
        self._runner_task = None

    async def _run_loop(self, interval: float) -> None:
        """Run the internal background pump loop.

        Description:
            Repeatedly drain queued events, then sleep for the configured
            interval until `stop()` clears the running flag.

        Example:
            await bridge._run_loop(0.05)

        Expected output:
            Queued events continue to flow without manual calls to
            `call_waiting_events()`.

        Caveats:
            This is an internal helper and is normally reached through `start()`.
        """
        while self._running:
            await self.call_waiting_events()
            await asyncio.sleep(interval)

    async def _dispatch_event(self, event: BridgeEvent) -> None:
        """Route bridge-owned event types to their handlers.

        Description:
            Examine the event type and invoke the matching internal handler for
            node calls or node results.

        Example:
            await bridge._dispatch_event(BridgeEvent(SimpleBridge.CALL_NODE, {...}))

        Expected output:
            Supported bridge event types trigger their internal handler.

        Caveats:
            Custom event types are not routed here; they only reach listeners.
        """
        if event.event_type == self.CALL_NODE:
            await self._handle_call_node(event)
            return

        if event.event_type == self.NODE_RESULT:
            await self._handle_node_result(event)

    async def _handle_call_node(self, event: BridgeEvent) -> None:
        """Execute one queued node call.

        Description:
            Resolve the target node, call its `graph_execute()` method, and
            convert the result into a queued node-result event.

        Example:
            event = BridgeEvent(SimpleBridge.CALL_NODE, {"node": PipRef("a", "foo"), "value": 1})
            await bridge._handle_call_node(event)

        Expected output:
            A follow-up `bridge:node_result` or `bridge:node_error` event is
            queued.

        Caveats:
            Node exceptions are swallowed here and converted into error events.
        """
        target = PipRef.from_value(event.payload["node"])
        value = event.payload.get("value")

        try:
            node = self.nodes[target.node_id]
            result = node.graph_execute(value, target.pip)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            self.push_event(
                self.NODE_ERROR,
                {
                    "node": target,
                    "value": value,
                    "error": str(exc),
                },
            )
            return

        self._emit_node_result(result, target)

    async def _handle_node_result(self, event: BridgeEvent) -> None:
        """Route one node result to its downstream connections.

        Description:
            Look up the next connected pips for the emitting source and enqueue
            matching node calls with the same value.

        Example:
            event = BridgeEvent(SimpleBridge.NODE_RESULT, {"node": PipRef("a", "foo"), "value": 1})
            await bridge._handle_node_result(event)

        Expected output:
            Downstream nodes connected to that exact pip are queued to run.

        Caveats:
            If no connection exists for the emitted pip, routing stops there.
        """
        origin = PipRef.from_value(event.payload["node"], default_pip="out")
        next_nodes = self.get_next(origin)
        if not next_nodes:
            return

        self.call_nodes_evented(next_nodes, event.payload.get("value"))

    def _emit_node_result(self, result: Any, target: PipRef) -> BridgeEvent:
        """Convert a node return value into one queued result event.

        Description:
            Interpret `NodeOutput` as an explicit outbound pip selection and
            treat all other values as a default `out` emission.

        Example:
            bridge._emit_node_result(NodeOutput("seed", pip="foo"), PipRef("node_a", "entry"))

        Expected output:
            A `bridge:node_result` event is queued from the chosen outbound pip.

        Caveats:
            This helper only handles one emission; multi-output fan-out would
            require a broader result contract.
        """
        if isinstance(result, NodeOutput):
            return self.emit_result(result.value, target, pip=result.pip)

        return self.emit_result(result, target)
