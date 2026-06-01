from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from typing import Callable

from .types import BridgeEvent


log = logging.getLogger(__name__)

EventCallback = Callable[[BridgeEvent], object]


class EventEmitter:
    """Publish bridge events to listeners.

    Description:
        Maintain per-event listeners and global listeners, then deliver events
        to them in registration order.

    Example:
        emitter = EventEmitter()
        unsubscribe = emitter.on("demo:start", lambda event: None)

    Expected output:
        Listeners registered with `on()` or `on_any()` are called when
        `emit()` runs.

    Caveats:
        Listener failures are logged and swallowed so one bad callback does not
        stop the rest.
    """

    def __init__(self) -> None:
        """Create an empty event emitter.

        Description:
            Initialize the internal listener stores used for typed and global
            subscriptions.

        Example:
            emitter = EventEmitter()

        Expected output:
            `emitter` starts with no registered listeners.

        Caveats:
            Listener order depends on the order you register callbacks.
        """
        self._listeners: dict[str, list[EventCallback]] = defaultdict(list)
        self._any_listeners: list[EventCallback] = []

    def on(self, event_type: str, callback: EventCallback) -> Callable[[], None]:
        """Subscribe one callback to one event type.

        Description:
            Register a callback that will fire only when an event with the
            matching type is emitted.

        Example:
            def handle(event):
                print(event.event_type)

            unsubscribe = emitter.on("demo:start", handle)

        Expected output:
            Returns an `unsubscribe()` function that removes the callback.

        Caveats:
            The callback may be synchronous or asynchronous.
        """
        self._listeners[event_type].append(callback)

        def unsubscribe() -> None:
            listeners = self._listeners.get(event_type, [])
            if callback in listeners:
                listeners.remove(callback)

        return unsubscribe

    def on_any(self, callback: EventCallback) -> Callable[[], None]:
        """Subscribe one callback to every emitted event.

        Description:
            Register a callback that runs for all event types handled by the
            emitter.

        Example:
            def log_event(event):
                print(event.event_type)

            unsubscribe = emitter.on_any(log_event)

        Expected output:
            Returns an `unsubscribe()` function that removes the callback.

        Caveats:
            This is useful for debugging, but it will observe all traffic.
        """
        self._any_listeners.append(callback)

        def unsubscribe() -> None:
            if callback in self._any_listeners:
                self._any_listeners.remove(callback)

        return unsubscribe

    async def emit(self, event: BridgeEvent) -> None:
        """Deliver one event to all matching listeners.

        Description:
            Call global listeners first, then listeners registered for the
            specific event type, awaiting async callbacks when needed.

        Example:
            event = BridgeEvent("demo:start", {"value": 1})
            await emitter.emit(event)

        Expected output:
            Each registered callback sees the same `BridgeEvent` instance.

        Caveats:
            Callbacks run serially, so a slow listener delays later listeners.
        """
        listeners = [
            *list(self._any_listeners),
            *list(self._listeners.get(event.event_type, [])),
        ]
        for callback in listeners:
            try:
                result = callback(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                log.exception("Event listener failed for %s", event.event_type)
