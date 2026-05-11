"""
event_system.py
──────────────────────────────────────────────────────────────────────────────
Event subscription and pub/sub for the power graph.

Provides a simple event emitter that mimics the JavaScript CustomEvent pattern,
allowing nodes and the graph to publish simulation events for monitoring and
debugging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Any
from collections import defaultdict


@dataclass
class Event:
    """Represents a power graph event."""
    type: str              # e.g. 'node:tick', 'signal:emit', 'graph:start'
    label: str = ''        # Source label (e.g. panel id)
    data: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Serialize event to dictionary."""
        return {
            'type': self.type,
            'label': self.label,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
        }


class EventEmitter:
    """Simple pub/sub event system."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._log: List[Event] = []
        self._max_log = 1000

    def on(self, event_type: str, callback: Callable) -> Callable:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type to listen for (e.g. 'signal:emit')
            callback: Function called when event fires

        Returns:
            Unsubscribe function
        """
        self._listeners[event_type].append(callback)

        def unsubscribe():
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)

        return unsubscribe

    def once(self, event_type: str, callback: Callable) -> Callable:
        """Subscribe to event, auto-unsubscribe after first fire."""
        def wrapper(event: Event):
            callback(event)
            unsubscribe()

        unsubscribe = self.on(event_type, wrapper)
        return unsubscribe

    def emit(self, event_type: str, label: str = '', data: Dict[str, Any] = None):
        """
        Publish an event.

        Args:
            event_type: Type of event
            label: Source label (e.g. panel/node id)
            data: Arbitrary event data
        """
        if data is None:
            data = {}

        event = Event(type=event_type, label=label, data=data)
        self._log.append(event)

        # Cap log size
        if len(self._log) > self._max_log:
            self._log = self._log[-self._max_log:]

        # Fire callbacks
        for callback in self._listeners.get(event_type, []):
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event listener for {event_type}: {e}")

    def get_log(self) -> List[Event]:
        """Get event log (newest first)."""
        return list(reversed(self._log))

    def clear_log(self):
        """Clear event log."""
        self._log.clear()

    def get_listeners(self, event_type: str = None) -> Dict:
        """Get listener counts by type."""
        if event_type:
            return {event_type: len(self._listeners.get(event_type, []))}
        return {k: len(v) for k, v in self._listeners.items()}


class EventMonitor:
    """
    Centralized event monitoring.

    Tracks events, statistics, and provides filtering/querying.
    """

    def __init__(self, emitter: EventEmitter = None):
        self.emitter = emitter or EventEmitter()
        self.enabled = True
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._events_per_second = 0
        self._bytes_per_second = 0

    def start(self):
        """Start monitoring."""
        self.enabled = True

    def stop(self):
        """Stop monitoring."""
        self.enabled = False

    def get_events(self, event_type: str = None, limit: int = 100) -> List[Event]:
        """
        Query events from log.

        Args:
            event_type: Filter by type (None = all)
            limit: Max events to return

        Returns:
            List of events (newest first)
        """
        if not self.enabled:
            return []

        log = self.emitter.get_log()
        if event_type:
            log = [e for e in log if e.type == event_type]
        return log[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'enabled': self.enabled,
            'event_counts': dict(self._event_counts),
            'events_per_second': self._events_per_second,
            'bytes_per_second': self._bytes_per_second,
            'total_events': sum(self._event_counts.values()),
        }

    def reset_stats(self):
        """Reset statistics."""
        self._event_counts.clear()
        self._events_per_second = 0
        self._bytes_per_second = 0
