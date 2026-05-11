"""
graph.py
──────────────────────────────────────────────────────────────────────────────
PowerGraph — central engine for the power-2 simulation.

Responsibilities:
  • Signal propagation: receive(), emit(), combineSources()
  • Generator draw BFS for load calculation
  • Ripple effects (voltage/current jitter)
  • Async tick loop for frame-based updates
  • Panel management: spawn, remove, reset
  • Connections and wiring

The graph maintains:
  - panels: List of all active panel state dicts
  - edges: Connection topology and properties
  - propagating: Cycle guard (set of in-flight panel IDs)
"""

import asyncio
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

from .node_registry import NodeRegistry
from .node_base import NodeBase, Signal, NOMINAL_VOLTS
from .edge_store import EdgeStore, get_edge_store
from .event_system import EventEmitter


def _ripple_random(amount: float) -> float:
    """Generate random ripple offset: ±amount."""
    import random
    return random.uniform(-amount, amount)


class PowerGraph:
    """Central simulation engine."""

    def __init__(self, event_emitter: EventEmitter = None):
        """
        Initialize the power graph.

        Args:
            event_emitter: EventEmitter instance (creates if None)
        """
        self.emitter = event_emitter or EventEmitter()
        NodeBase._emitter = self.emitter
        self.edge_store = get_edge_store()

        # Panel state
        self.panels: List[Dict] = []
        self._uid = 0  # Panel ID counter
        self._next_id = 1

        # Connections: {(from_id, from_pip) : [(to_id, to_pip, conn_key), ...]}
        self._connections: Dict[Tuple[int, int], List[Tuple[int, int, str]]] = defaultdict(list)

        # Cycle guard for signal propagation
        self._propagating: Set[int] = set()

        # Async loop state
        self._running = False
        self._tick_handle = None
        self._last_tick_time = None
        self._target_fps = 60

    # ────────────────────────────────────────────────────────────────────────
    # PANEL MANAGEMENT
    # ────────────────────────────────────────────────────────────────────────

    def spawn(self, node_type: str, label: str = None, preset: Dict = None) -> Dict:
        """
        Create and add a new panel to the graph.

        Args:
            node_type: Type of node (e.g. 'gen', 'bulb', 'load')
            label: Optional label override
            preset: Catalog preset dict

        Returns:
            Panel state dict (now in self.panels)

        Raises:
            ValueError: If node_type not registered
        """
        panel_id = self._next_id
        self._next_id += 1

        if preset is None:
            preset = {}

        if label:
            preset['label'] = label

        panel = NodeRegistry.create(node_type, panel_id, preset)
        if panel is None:
            raise ValueError(f"Cannot create node of type {node_type}")

        self.panels.append(panel)
        self.emitter.emit('graph:spawn', f"panel-{panel_id}", {'type': node_type, 'label': panel.get('label')})

        return panel

    def remove(self, panel_id: int) -> bool:
        """
        Remove a panel from the graph.

        Args:
            panel_id: Panel ID to remove

        Returns:
            True if removed, False if not found
        """
        panel = self._find_panel(panel_id)
        if not panel:
            return False

        # Remove all connections involving this panel
        connections_to_remove = []
        for key, conn_list in list(self._connections.items()):
            from_id = key[0]
            if from_id == panel_id:
                connections_to_remove.extend([c[2] for c in conn_list])
            else:
                # Filter out connections to this panel
                self._connections[key] = [c for c in conn_list if c[0] != panel_id]

        for key in connections_to_remove:
            self.edge_store.remove(key)

        self.panels = [p for p in self.panels if p['id'] != panel_id]
        self.emitter.emit('graph:remove', f"panel-{panel_id}")

        return True

    def reset(self):
        """Reset all panels to initial state."""
        for panel in self.panels:
            node_cls = NodeRegistry.get(panel['type'])
            if node_cls:
                node_cls.reset(panel, self)
        self.emitter.emit('graph:reset')

    # ────────────────────────────────────────────────────────────────────────
    # CONNECTIONS & WIRING
    # ────────────────────────────────────────────────────────────────────────

    def connect(
        self,
        from_panel: Dict,
        from_pip: int,
        to_panel: Dict,
        to_pip: int,
        **edge_props
    ) -> str:
        """
        Create a connection (wire) between two panels.

        Args:
            from_panel: Source panel dict
            from_pip: Outbound pip index
            to_panel: Destination panel dict
            to_pip: Inbound pip index
            **edge_props: Wire properties (wireType='copper', length=0, etc.)

        Returns:
            Connection key
        """
        from_id = from_panel['id']
        to_id = to_panel['id']

        # Create connection key
        conn_key = f"{from_id}:{from_pip}->{to_id}:{to_pip}"

        # Store in topology
        key = (from_id, from_pip)
        self._connections[key].append((to_id, to_pip, conn_key))

        # Create edge properties
        self.edge_store.update(conn_key, edge_props)

        self.emitter.emit(
            'graph:connect',
            conn_key,
            {'from': from_id, 'to': to_id, 'wireType': edge_props.get('wireType', 'copper')}
        )

        return conn_key

    def disconnect(self, conn_key: str) -> bool:
        """
        Remove a connection.

        Args:
            conn_key: Connection key

        Returns:
            True if removed, False if not found
        """
        # Parse key: "from_id:from_pip->to_id:to_pip"
        parts = conn_key.split('->')
        if len(parts) != 2:
            return False

        from_part, to_part = parts
        try:
            from_id, from_pip = map(int, from_part.split(':'))
            to_id, _ = map(int, to_part.split(':'))
        except ValueError:
            return False

        key = (from_id, from_pip)
        if key not in self._connections:
            return False

        # Find and remove the connection
        original_len = len(self._connections[key])
        self._connections[key] = [c for c in self._connections[key] if c[2] != conn_key]

        if len(self._connections[key]) < original_len:
            self.edge_store.remove(conn_key)
            self.emitter.emit('graph:disconnect', conn_key)
            return True

        return False

    # ────────────────────────────────────────────────────────────────────────
    # SIGNAL PROPAGATION
    # ────────────────────────────────────────────────────────────────────────

    def _find_panel(self, panel_id: int) -> Optional[Dict]:
        """Find a panel by ID."""
        for p in self.panels:
            if p['id'] == panel_id:
                return p
        return None

    def receive(
        self,
        panel: Dict,
        signal: Signal,
        source_id: Optional[int] = None,
        in_pip_index: int = 0
    ):
        """
        Deliver a signal to a panel, re-combine sources, then apply node logic.

        Args:
            panel: Destination panel
            signal: {v, a} or None
            source_id: Panel ID of upstream sender
            in_pip_index: Inbound pip index that was connected
        """
        # Cycle guard: prevent infinite loops in ring topologies
        if panel['id'] in self._propagating:
            return

        self._propagating.add(panel['id'])
        try:
            # Store signal from this source — always use str keys so JSON-loaded
            # powerSources (str keys) and runtime-set entries remain consistent.
            if source_id is not None:
                src_key = str(source_id)
                if signal is None:
                    panel['powerSources'].pop(src_key, None)
                else:
                    panel['powerSources'][src_key] = signal

            # Let multi-input nodes know which pip fired
            panel['_last_in_pip'] = in_pip_index

            # Combine all incoming sources
            combined = self.combine_sources(panel['powerSources'])
            panel['signal'] = combined

            # Get node class and apply logic
            node_cls = NodeRegistry.get(panel['type'])
            if not node_cls:
                return

            # Handle disabled state
            if panel.get('enabled') is False:
                panel['state'] = 'off'
                if hasattr(node_cls, 'on_disabled'):
                    node_cls.on_disabled(panel, self)
                else:
                    self.emit(panel, None)
                return

            # Apply node-specific logic
            node_cls.apply(panel, combined, self)

        finally:
            self._propagating.discard(panel['id'])

    def emit(self, panel: Dict, signal: Signal):
        """
        Forward signal from panel's outbound pip(s) to all connected targets.

        Args:
            panel: Source panel
            signal: {v, a} or None
        """
        source_id = panel['id']
        connections = self._connections.get((source_id, 0), [])

        for to_id, to_pip, conn_key in connections:
            target = self._find_panel(to_id)
            if target:
                transformed = self.edge_store.apply_edge(signal, conn_key)
                self.receive(target, transformed, source_id, to_pip)

        self.emitter.emit('graph:emit', f"panel-{source_id}", {'signal': signal})

    def emit_to(self, panel: Dict, pip_index: int, signal: Signal):
        """
        Forward signal from a specific outbound pip index.

        Used by multi-output nodes (e.g. decisions) to route to chosen output.
        Source ID is "panel_id:pipIndex" so downstream tracks each pip separately.

        Args:
            panel: Source panel
            pip_index: Outbound pip index
            signal: Signal to emit
        """
        source_id = panel['id']
        connections = self._connections.get((source_id, pip_index), [])

        for to_id, to_pip, conn_key in connections:
            target = self._find_panel(to_id)
            if target:
                # Use composite source ID
                composite_source = f"{source_id}:{pip_index}"
                transformed = self.edge_store.apply_edge(signal, conn_key)
                self.receive(target, transformed, source_id, to_pip)

    # Alias used by multi-output nodes
    emit_pip = emit_to

    def combine_sources(self, sources: Dict[int, Signal]) -> Signal:
        """
        Fold multiple upstream source signals into one combined {v, a}.

        Folding rules:
          v = max voltage across all live sources (dominant-rail model)
          a = sum of available amps from all live sources (parallel supply)

        Returns:
            Combined {v, a} or None if no live sources
        """
        live = [s for s in sources.values() if s and s.get('v', 0) > 0]

        if not live:
            return None

        return {
            'v': max(s.get('v', 0) for s in live),
            'a': sum(s.get('a', 0) for s in live),
        }

    def repropagate_all(self):
        """
        Re-broadcast from every generator and enabled source after topology change.

        Dead/disabled generators emit None so downstream powerSources entries are
        cleared — otherwise stale amps continue to appear at loads.
        """
        for panel in self.panels:
            if panel['type'] in ('gen', 'series-battery'):
                if panel.get('live') and panel.get('enabled', True) is not False:
                    self.emit(panel, {'v': panel.get('volts', 240), 'a': panel.get('amps', 13)})
                else:
                    self.emit(panel, None)
            elif panel.get('enabled') is False:
                self.emit(panel, None)

    # ────────────────────────────────────────────────────────────────────────
    # GENERATOR DRAW (BFS)
    # ────────────────────────────────────────────────────────────────────────

    def update_all_gen_draws(self):
        """Recompute draw watts for every generator and battery."""
        for p in self.panels:
            if p['type'] in ('gen', 'series-battery'):
                self.compute_gen_draw(p)

    def compute_gen_draw(self, gen: Dict):
        """
        BFS from a generator's outbound pips, summing load contributions.

        Args:
            gen: Generator panel
        """
        visited: Set[int] = set()
        queue: List[int] = [gen['id']]
        total_w = 0

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)

            panel = self._find_panel(node_id)
            if not panel:
                continue

            # shareCount: load fed by N generators is 1/N attributed to each
            share_count = max(1, len(panel.get('powerSources', {})))

            # Count bulb watts
            if panel['type'] == 'bulb' and panel.get('state') in ('on', 'dim'):
                total_w += panel.get('watts', 0) / share_count

            # Count load watts
            node_cls = NodeRegistry.get(panel['type'])
            if node_cls and hasattr(node_cls, 'consumes_watts') and node_cls.consumes_watts:
                state = panel.get('state')
                if state in ('on', 'capacitor'):
                    total_w += panel.get('current_watts', panel.get('watts', 0)) / share_count

            # Enqueue downstream panels
            for pip in panel.get('pipsOutbound', []):
                pip_idx = pip.get('index', 0)
                for to_id, _, _ in self._connections.get((node_id, pip_idx), []):
                    if to_id not in visited:
                        queue.append(to_id)

        gen['drawWatts'] = round(total_w, 1)
        gen['drawAmps'] = round(total_w / gen.get('volts', 240), 2) if gen.get('volts', 240) > 0 else 0

        # Apply load-based state changes
        if gen.get('live'):
            ratio = gen['drawAmps'] / gen.get('amps', 13)

            if ratio > 1.3:
                if gen.get('state') != 'tripped':
                    gen['overload'] = True
                    gen['state'] = 'tripped'
                    self.emit(gen, None)
            elif ratio > 1.0:
                sag_volts = round(gen.get('volts', 240) * 0.85, 1)
                gen['overload'] = True
                gen['state'] = 'sag'
                self.emit(gen, {'v': sag_volts, 'a': gen.get('amps', 13)})
            else:
                # Proportional micro-sag: voltage drops slightly under load,
                # rippling load noise through the circuit to all downstream nodes.
                prev_draw = gen.get('_prev_draw_watts', -1.0)
                draw_changed = abs(gen['drawWatts'] - prev_draw) > 5.0
                if draw_changed and gen.get('enabled', True) is not False:
                    load_ratio = min(1.0, ratio)
                    v_out = round(gen.get('volts', 240) * (1.0 - load_ratio * 0.05), 2)
                    self.emit(gen, {'v': v_out, 'a': gen.get('amps', 13)})

                if gen.get('overload'):
                    gen['overload'] = False
                    gen['state'] = 'on'
                    self.emit(gen, {'v': gen.get('volts', 240), 'a': gen.get('amps', 13)})
                else:
                    gen['state'] = 'on'

            gen['_prev_draw_watts'] = gen['drawWatts']

    # ────────────────────────────────────────────────────────────────────────
    # RIPPLE EFFECTS
    # ────────────────────────────────────────────────────────────────────────

    def _tick_ripple(self, dt: float):
        """Apply ripple (jitter) effects to generator and load voltages."""
        for panel in self.panels:
            ripple = panel.get('ripple')
            if not ripple or not ripple.get('enabled'):
                continue

            panel['_ripple_accum'] = panel.get('_ripple_accum', 0) + dt
            if panel['_ripple_accum'] < ripple.get('interval', 1.0):
                continue

            panel['_ripple_accum'] = 0
            panel['_ripple_offset'] = _ripple_random(ripple.get('amount', 1.0))

            # Generator ripple
            if panel['type'] == 'gen' and panel.get('live') and panel.get('state') != 'tripped':
                v_out = max(1, panel.get('volts', 240) + panel['_ripple_offset'])
                self.emit(panel, {'v': v_out, 'a': panel.get('amps', 13)})

            # Load ripple
            if panel['type'] == 'load' and panel.get('state') == 'on' and panel.get('signal'):
                draw_amps = panel.get('watts', 0) / NOMINAL_VOLTS
                amp_jitter = _ripple_random(ripple.get('amount', 1.0) / NOMINAL_VOLTS)
                a_out = max(0, panel['signal'].get('a', 0) - draw_amps + amp_jitter)
                self.emit(panel, {'v': panel['signal'].get('v', 240), 'a': a_out})

            # Converter and battery ripple can call apply() to regenerate
            if panel['type'] in ('converter', 'series-battery') and panel.get('signal'):
                node_cls = NodeRegistry.get(panel['type'])
                if node_cls:
                    node_cls.apply(panel, panel['signal'], self)

    # ────────────────────────────────────────────────────────────────────────
    # ASYNC TICK LOOP
    # ────────────────────────────────────────────────────────────────────────

    async def _tick_loop(self):
        """Main simulation loop."""
        self._last_tick_time = time.time()

        while self._running:
            now = time.time()
            dt = min(now - self._last_tick_time, 0.1)  # Cap dt at 100ms
            self._last_tick_time = now

            # Apply ripple effects
            self._tick_ripple(dt)

            # Tick each node
            for panel in self.panels:
                node_cls = NodeRegistry.get(panel['type'])
                if node_cls:
                    node_cls.tick(panel, dt, self)

            # Recompute generator draws
            self.update_all_gen_draws()

            # Sleep to maintain target FPS
            frame_time = 1.0 / self._target_fps
            await asyncio.sleep(max(0, frame_time - (time.time() - now)))

    async def run(self, duration: float = None, fps: int = 60):
        """
        Run the simulation.

        Args:
            duration: Simulation duration in seconds (None = infinite)
            fps: Target frames per second (default 60)
        """
        self._running = True
        self._target_fps = fps
        self._last_tick_time = None

        self.emitter.emit('graph:start', label='graph')

        try:
            if duration is None:
                await self._tick_loop()
            else:
                start_time = time.time()
                while time.time() - start_time < duration and self._running:
                    await self._tick_loop()
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            self.emitter.emit('graph:stop', label='graph')

    def start(self):
        """Start the simulation (creates async task, returns immediately)."""
        if self._running:
            return
        self._running = True
        self.emitter.emit('graph:start', label='graph')

    def stop(self):
        """Stop the simulation."""
        self._running = False
        self.emitter.emit('graph:stop', label='graph')

    def is_running(self) -> bool:
        """Check if simulation is running."""
        return self._running

    # ────────────────────────────────────────────────────────────────────────
    # STATE SERIALIZATION (save/load)
    # ────────────────────────────────────────────────────────────────────────

    def export_json(self) -> Dict:
        """Export graph state to JSON-serializable dict."""
        nodes = []
        for panel in self.panels:
            node_cls = NodeRegistry.get(panel['type'])
            config_fields = node_cls.config_fields() if node_cls else []

            node_data = {
                'id': panel['id'],
                'type': panel['type'],
                'config': {k: panel.get(k) for k in config_fields},
            }
            nodes.append(node_data)

        # Connections
        connections = []
        for (from_id, from_pip), conn_list in self._connections.items():
            for to_id, to_pip, conn_key in conn_list:
                edge = self.edge_store.get(conn_key)
                connections.append({
                    'from': from_id,
                    'fromPip': from_pip,
                    'to': to_id,
                    'toPip': to_pip,
                    'edge': edge or {},
                })

        return {'nodes': nodes, 'connections': connections}

    def import_json(self, data: Dict):
        """Import graph state from exported JSON."""
        self.panels.clear()
        self._connections.clear()
        self.edge_store._store.clear()

        # Import nodes
        node_map = {}
        for node_data in data.get('nodes', []):
            node_type = node_data['type']
            node_id = node_data['id']
            config = node_data.get('config', {})

            node = NodeRegistry.create(node_type, node_id, config)
            if node:
                self.panels.append(node)
                node_map[node_id] = node
                self._next_id = max(self._next_id, node_id + 1)

        # Import connections
        for conn_data in data.get('connections', []):
            from_id = conn_data['from']
            to_id = conn_data['to']
            from_pip = conn_data.get('fromPip', 0)
            to_pip = conn_data.get('toPip', 0)
            edge = conn_data.get('edge', {})

            from_panel = node_map.get(from_id)
            to_panel = node_map.get(to_id)

            if from_panel and to_panel:
                self.connect(from_panel, from_pip, to_panel, to_pip, **edge)
