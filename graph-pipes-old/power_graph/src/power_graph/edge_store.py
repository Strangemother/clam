"""
edge_store.py
──────────────────────────────────────────────────────────────────────────────
Wire properties and signal transformation.

Each wire (connection) in the graph has properties that affect how signals
propagate:
  - enabled: bool — false = broken wire (passes null)
  - wireType: str — key from WIRE_TYPES catalog
  - length: float — distance in pixels (for resistance calculation)
  - manualResistance: float|None — overrides computed resistance

Signal Transformation
──────────────────────
R (Ω) = (length / PX_PER_UNIT) × ohmsPerUnit
V_out = V_in − (I × R)           ← resistive voltage drop
A_out = A_in                     ← amps pass through unchanged

If V_out ≤ 0 the function returns None (wire too resistive for the load).

Example
─────────
Wire: copper (0.005 Ω/unit), 300 px long, carrying 10 A at 240 V
  R      = (300 / 100) × 0.005  = 0.015 Ω
  V_drop = 10 A × 0.015 Ω      = 0.15 V
  V_out  = 240 − 0.15           = 239.85 V
  A_out  = 10 A  (unchanged)

PX_PER_UNIT = 100, so every 100 pixels of wire length equals one resistance unit.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class WireType:
    """Wire type catalog entry."""
    key: str
    label: str
    ohms_per_unit: float
    color: str = '#000000'


# Standard wire types
WIRE_TYPES = [
    WireType(key='copper', label='Copper', ohms_per_unit=0.005, color='#00e87c'),
    WireType(key='aluminium', label='Aluminium', ohms_per_unit=0.010, color='#aadd00'),
    WireType(key='steel', label='Steel', ohms_per_unit=0.080, color='#ff9900'),
    WireType(key='lossy', label='Lossy Cable', ohms_per_unit=0.300, color='#ff3333'),
]

# Conversion factor: 1 resistance unit = 100 pixels
PX_PER_UNIT = 100


class EdgeStore:
    """
    Stores and manages wire (edge) properties for all connections in the graph.
    """

    def __init__(self):
        self._store: Dict[str, dict] = {}
        self._wire_types = {wt.key: wt for wt in WIRE_TYPES}

    @staticmethod
    def _defaults() -> dict:
        """Default edge properties."""
        return {
            'enabled': True,
            'wireType': 'copper',
            'length': 0.0,
            'manualResistance': None,
        }

    def get_or_create(self, conn_key: str) -> dict:
        """Get or create edge properties for a connection key."""
        if conn_key not in self._store:
            self._store[conn_key] = self._defaults()
        return self._store[conn_key]

    def get(self, conn_key: str) -> Optional[dict]:
        """Get edge properties, or None if not found."""
        return self._store.get(conn_key)

    def update(self, conn_key: str, props: dict) -> dict:
        """Update edge properties."""
        edge = self.get_or_create(conn_key)
        edge.update(props)
        return edge

    def remove(self, conn_key: str):
        """Remove edge properties."""
        if conn_key in self._store:
            del self._store[conn_key]

    def compute_resistance(self, edge: dict) -> float:
        """
        Compute effective wire resistance in Ω.

        Args:
            edge: Edge properties dict

        Returns:
            Resistance in ohms
        """
        # Manual override takes precedence
        if edge.get('manualResistance') is not None:
            return float(edge['manualResistance'])

        # Look up wire type
        wire_type_key = edge.get('wireType', 'copper')
        wire_type = self._wire_types.get(wire_type_key)
        if not wire_type:
            wire_type = self._wire_types['copper']

        # R = (length / PX_PER_UNIT) × ohmsPerUnit
        length = edge.get('length', 0)
        resistance = (length / PX_PER_UNIT) * wire_type.ohms_per_unit
        return round(resistance, 4)

    def apply_edge(self, signal: Optional[dict], conn_key: str) -> Optional[dict]:
        """
        Apply edge transformation to signal (resistance drop).

        Args:
            signal: {v: volts, a: amps} or None
            conn_key: Connection key

        Returns:
            Transformed signal or None if wire is disabled or voltage drops to 0
        """
        if signal is None:
            return None

        edge = self.get(conn_key)
        if not edge or not edge.get('enabled', True):
            return None

        v = signal.get('v', 0)
        a = signal.get('a', 0)

        # Compute resistance and voltage drop
        r = self.compute_resistance(edge)
        v_drop = a * r
        v_out = v - v_drop

        # If voltage drops to 0 or below, signal is absorbed
        if v_out <= 0:
            return None

        return {
            'v': round(v_out, 2),
            'a': a,  # Amps pass through unchanged
        }

    def get_wire_types(self) -> Dict[str, WireType]:
        """Get all available wire types."""
        return dict(self._wire_types)

    def get_wire_type(self, key: str) -> Optional[WireType]:
        """Get a specific wire type."""
        return self._wire_types.get(key)


# Global singleton for convenience
_edge_store = EdgeStore()


def get_edge_store() -> EdgeStore:
    """Get the global edge store singleton."""
    return _edge_store
