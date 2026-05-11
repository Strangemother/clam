"""
node_base.py
──────────────────────────────────────────────────────────────────────────────
NodeBase — root class for every graph node in the power-2 system.

Architecture
────────────
Node state lives in plain dicts (panel state objects).
Node *behaviour* lives in class methods on each node class.
This separation means:
  • State management is simple and serializable
  • Node classes are stateless — easy to extend and test

To create a new node type:
  1. Extend NodeBase (or a suitable subclass like Load)
  2. Set class attributes: type, label, group, catalog
  3. Override defaults(id, preset) — call super().defaults() first
  4. Override apply(panel, signal, graph) for signal logic
  5. Optionally override tick(panel, dt, graph) for frame updates
  6. Call NodeRegistry.register(YourClass)

For single-unit variants, subclass the type family and set a new type:

    class Relay(Breaker):
        type = 'relay'
        label = 'Relay'
        catalog = [{'key': 'relay', 'label': 'Relay 10A', 'ratingAmps': 10}]

    NodeRegistry.register(Relay)

Signal format: {v: voltage, a: amps} or None
"""

import time
from typing import Dict, List, Optional, Any, ClassVar
from dataclasses import dataclass


# Type alias for signal dict
Signal = Optional[Dict[str, float]]

# Default nominal volts for W→A conversion
NOMINAL_VOLTS = 240


@dataclass
class RippleProfile:
    """Voltage/current ripple effect for realism."""
    enabled: bool = False
    amount: float = 1.0
    interval: float = 1.0


@dataclass
class SpikeProfile:
    """Inrush current spike on power up."""
    enabled: bool = False
    percent: float = 0.0
    duration: float = 0.5


class NodeBase:
    """
    Root class for all graph nodes.

    Node state lives in plain dicts (panel state objects).
    Node behaviour lives in classmethods — stateless singletons.

    Type families vs single-unit classes
    ─────────────────────────────────────
    A "type family" class (e.g. Breaker) holds a catalog of presets for
    several variants (6A, 13A, 30A breakers) all sharing the same type key.
    A "single-unit" class subclasses the family for isolated custom behaviour:

        class Relay(Breaker):
            type  = 'relay'
            label = 'Relay'
            catalog = [{'key': 'relay', 'label': 'Relay 10A', 'ratingAmps': 10}]

        NodeRegistry.register(Relay)

    Relay inherits all of Breaker's apply/tick/reset logic but is its own
    registered type, independently configurable with any override needed.
    """

    # ── Class attributes (override in subclasses) ────────────────────────────

    type: ClassVar[str] = 'base'
    label: ClassVar[str] = 'Node'
    group: ClassVar[str] = 'General'

    # Catalog preset entries — each entry is spread into defaults() as preset.
    catalog: ClassVar[List[Dict[str, Any]]] = []

    # Debounce / throttle period in milliseconds (override per subclass)
    dispatch_delay: ClassVar[int] = 100

    # Set by PowerGraph at construction — shared across all node classes
    _emitter: ClassVar[Any] = None

    # Throttle cooldown end-times: {panel_id:event_type → monotonic deadline}
    _throttle_until: ClassVar[Dict[str, float]] = {}

    # ── Defaults and profiles ────────────────────────────────────────────────

    @classmethod
    def defaults(cls, node_id: int, preset: Dict = None) -> Dict:
        """
        Returns the initial state object for a new panel of this type.

        Subclasses should call super().defaults() first then update/extend.

        Args:
            node_id: Unique panel ID
            preset:  Catalog preset dict (or {})

        Returns:
            Initial panel state dict
        """
        if preset is None:
            preset = {}

        return {
            'id':           node_id,
            'type':         cls.type,
            'label':        preset.get('label', cls.label),
            'enabled':      True,
            'signal':       None,
            'powerSources': {},
            'state':        'off',
            'ripple':       {**cls._default_ripple().__dict__},
            'spike':        {**cls._default_spike().__dict__},
            '_ripple_accum':  0,
            '_ripple_offset': 0,
            '_spike_timer':   0,
            'pipsInbound':  cls._default_pips_inbound(node_id),
            'pipsOutbound': cls._default_pips_outbound(node_id),
        }

    @classmethod
    def _default_ripple(cls) -> RippleProfile:
        """Override to change the default ripple profile for this type."""
        return RippleProfile(enabled=False, amount=1.0, interval=1.0)

    @classmethod
    def _default_spike(cls) -> SpikeProfile:
        """Override to set startup inrush spike defaults for this type."""
        return SpikeProfile(enabled=False, percent=0, duration=0.5)

    @classmethod
    def _default_pips_inbound(cls, node_id: int) -> List[Dict]:
        """Override to suppress inbound pips (Generator has none)."""
        return [{'label': node_id, 'index': 0}]

    @classmethod
    def _default_pips_outbound(cls, node_id: int) -> List[Dict]:
        """Override to suppress outbound pips (Bulb is a sink)."""
        return [{'label': node_id, 'index': 0}]

    # ── Spike (inrush current) helpers ───────────────────────────────────────

    @staticmethod
    def start_spike(panel: Dict):
        """Begin an inrush spike at the moment a node turns on."""
        spike = panel.get('spike', {})
        if not spike.get('enabled') or not spike.get('percent', 0):
            return
        panel['_spike_timer'] = spike.get('duration', 0.5)

    @staticmethod
    def tick_spike(panel: Dict, dt: float) -> bool:
        """
        Decay the spike timer by dt.

        Returns:
            True if spike is still active after this tick
        """
        timer = panel.get('_spike_timer', 0)
        if timer <= 0:
            return False
        panel['_spike_timer'] = max(0.0, timer - dt)
        return panel['_spike_timer'] > 0

    @staticmethod
    def spike_multiplier(panel: Dict) -> float:
        """
        Current inrush multiplier — linearly decays from (1 + percent/100) → 1.0.

        Returns:
            Multiplier (1.0 when no spike is active)
        """
        timer = panel.get('_spike_timer', 0)
        if timer <= 0:
            return 1.0
        spike    = panel.get('spike', {})
        duration = spike.get('duration', 0.5)
        percent  = spike.get('percent', 0)
        frac     = (timer / duration) if duration > 0 else 0
        return 1.0 + (percent / 100) * frac

    # ── Event dispatch ───────────────────────────────────────────────────────

    @classmethod
    def dispatch(cls, panel: Dict, event_type: str, data: Dict = None):
        """
        Emit a debounced event via the shared emitter.

        Fires at most once per dispatch_delay ms per (panel × event_type).
        Newest call wins — mirrors the JS setTimeout debounce pattern.

        Args:
            panel:      Panel state dict (provides id and type)
            event_type: Dot-namespaced event string e.g. 'state:change'
            data:       Serialisable payload dict
        """
        if not panel.get('enabled', True):
            return
        if cls._emitter is None:
            return

        key      = f"{panel['id']}:{event_type}"
        delay    = getattr(cls, 'dispatch_delay', NodeBase.dispatch_delay) / 1000
        now      = time.monotonic()
        deadline = cls._throttle_until.get(key, 0)

        if now < deadline:
            # Still in cooldown — update the pending payload so newest wins
            cls._throttle_until[key] = now + delay
            return

        cls._throttle_until[key] = now + delay
        cls._emitter.emit(
            event_type,
            f"{panel['type']}:{panel['id']}",
            data or {},
        )

    @classmethod
    def throttle(cls, panel: Dict, event_type: str, data: Dict = None):
        """
        Emit a throttled event: fire immediately, suppress for dispatch_delay ms.

        Use for continuous streaming values (temperature, voltage) where you
        want the first update through and then a cooldown — not the latest.

        Args:
            panel:      Panel state dict
            event_type: Event name
            data:       Payload dict
        """
        if not panel.get('enabled', True):
            return
        if cls._emitter is None:
            return

        key   = f"{panel['id']}:{event_type}"
        delay = getattr(cls, 'dispatch_delay', NodeBase.dispatch_delay) / 1000
        now   = time.monotonic()

        if now < cls._throttle_until.get(key, 0):
            return  # In cooldown — skip

        cls._throttle_until[key] = now + delay
        cls._emitter.emit(
            event_type,
            f"{panel['type']}:{panel['id']}",
            data or {},
        )

    # ── Serialization ────────────────────────────────────────────────────────

    @classmethod
    def config_fields(cls) -> List[str]:
        """
        List of panel field names to include in save/load serialisation.

        Contract:
          • Only list configuration fields (user-set, persist across reloads)
          • Do NOT include runtime state or _ prefixed fields
          • Subclasses extend: return [*super().config_fields(), 'myField']

        Returns:
            List of field names to serialize
        """
        return ['label', 'enabled']

    # ── Signal processing ────────────────────────────────────────────────────

    @classmethod
    def apply(cls, panel: Dict, signal: Signal, graph):
        """
        Process an incoming combined signal and update panel state.

        Must call graph.emit() or graph.emit_to() to forward power.

        Args:
            panel:  Panel state dict
            signal: Combined {v, a} or None
            graph:  PowerGraph engine (emit, update_all_gen_draws, …)
        """
        graph.emit(panel, signal)  # default: transparent pass-through

    @classmethod
    def tick(cls, panel: Dict, dt: float, graph):
        """
        Per-frame update (~60 fps). Override for time-driven behaviour.

        Args:
            panel: Panel state
            dt:    Delta time in seconds (capped ≤ 0.1)
            graph: PowerGraph engine
        """

    @classmethod
    def on_disabled(cls, panel: Dict, graph):
        """Called when enabled=False. Default: emit null downstream."""
        graph.emit(panel, None)

    @classmethod
    def reset(cls, panel: Dict, graph):
        """
        Reset node to off state without altering config fields.
        Subclasses should call super().reset() then clear their own extras.
        """
        panel['signal']       = None
        panel['powerSources'] = {}
        panel['state']        = 'off'
        panel['_ripple_accum'] = 0
        panel['_spike_timer']  = 0
        graph.emit(panel, None)
