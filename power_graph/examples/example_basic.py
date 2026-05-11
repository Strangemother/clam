"""
example_basic.py
──────────────────────────────────────────────────────────────────────────────
Basic example of the Python Power Graph system.

Demonstrates:
  1. Creating a graph
  2. Spawning nodes (generator, loads, bulbs)
  3. Connecting them with wires
  4. Running the simulation with async loop
  5. Monitoring events

Usage:
    python power_graph/examples/example_basic.py
    python -m power_graph.examples.example_basic
"""

import asyncio
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

# Import the power graph system
from power_graph import PowerGraph, NodeRegistry
from power_graph.event_system import EventMonitor
from power_graph.nodes import Generator, Bulb, Load, Breaker


async def main():
    """Run a basic power simulation."""

    print("=" * 70)
    print("Python Power Graph - Basic Example")
    print("=" * 70)
    print()

    # Create graph with event system
    graph = PowerGraph()
    monitor = EventMonitor(graph.emitter)

    # Create nodes
    print("Creating nodes...")
    gen = graph.spawn('gen', label='Power Generator')
    gen['volts'] = 240
    gen['amps'] = 13
    gen['live'] = True

    bulb1 = graph.spawn('bulb', label='Living Room Light')
    bulb1['watts'] = 60

    bulb2 = graph.spawn('bulb', label='Kitchen Light')
    bulb2['watts'] = 100

    load = graph.spawn('load', label='Central Heater')
    load['watts'] = 3000
    load['minVolts'] = 200

    breaker = graph.spawn('breaker', label='Main Breaker')
    breaker['ratingAmps'] = 15

    print(f"  ✓ Generator: {gen['label']} ({gen['volts']}V @ {gen['amps']}A)")
    print(f"  ✓ Bulbs: {bulb1['label']} + {bulb2['label']}")
    print(f"  ✓ Load: {load['label']} ({load['watts']}W)")
    print(f"  ✓ Breaker: {breaker['label']} ({breaker['ratingAmps']}A rating)")
    print()

    # Connect nodes
    print("Wiring nodes...")
    graph.connect(gen, 0, breaker, 0, wireType='copper', length=100)
    graph.connect(breaker, 0, bulb1, 0, wireType='copper', length=50)
    graph.connect(breaker, 0, bulb2, 0, wireType='copper', length=75)
    graph.connect(breaker, 0, load, 0, wireType='copper', length=200)
    print("  ✓ Gen → Breaker → Bulbs & Load")
    print()

    # Hook event listeners for interesting events
    def on_receive(event):
        pass  # Suppress noise for now

    def on_emit(event):
        if event.data:
            v = event.data.get('v', 0)
            a = event.data.get('a', 0)
            # print(f"  ◦ {event.label}: {v:.1f}V @ {a:.2f}A")

    graph.emitter.on('graph:emit', on_emit)

    # Run simulation
    print("Starting simulation for 5 seconds...")
    print("-" * 70)

    # Set up summary printing
    last_print = [0]

    def on_tick():
        now = graph._last_tick_time or 0
        if now - last_print[0] > 1.0:  # Print every second
            last_print[0] = now

            print(f"\nTime: {now:.1f}s")
            for panel in graph.panels:
                if panel['type'] == 'gen':
                    print(f"  Generator: {panel['state'].upper()} | "
                          f"Draw: {panel['drawWatts']:.0f}W @ {panel['drawAmps']:.2f}A")
                elif panel['type'] == 'bulb':
                    print(f"  {panel['label']}: {panel['state'].upper()} | "
                          f"Signal: {panel['signal']}")
                elif panel['type'] == 'load':
                    print(f"  {panel['label']}: {panel['state'].upper()} | "
                          f"Consuming: {panel.get('current_watts', 0):.0f}W")
                elif panel['type'] == 'breaker':
                    print(f"  {panel['label']}: {panel['state'].upper()}")

    # Monkey-patch the tick loop to add our callback
    original_tick_loop = graph._tick_loop

    async def tick_loop_with_callback():
        graph._last_tick_time = __import__('time').time()
        while graph._running:
            await original_tick_loop()
            on_tick()

    graph._tick_loop = tick_loop_with_callback

    # Run simulation
    try:
        await graph.run(duration=5, fps=10)
    except KeyboardInterrupt:
        pass

    print()
    print("-" * 70)
    print("Simulation complete!")
    print()

    # Print summary stats
    print("Final State:")
    for panel in graph.panels:
        print(f"  {panel['label']} ({panel['type']}): state={panel['state']}")

    print()
    print("Event Log Stats:")
    stats = monitor.get_stats()
    print(f"  Total events: {stats['total_events']}")
    print(f"  Event types: {len(stats['event_counts'])}")
    for event_type, count in sorted(stats['event_counts'].items()):
        print(f"    - {event_type}: {count}")

    print()
    print("=" * 70)


async def test_overcurrent():
    """Test circuit breaker protection."""
    print()
    print("=" * 70)
    print("Test: Circuit Breaker Overcurrent Protection")
    print("=" * 70)
    print()

    graph = PowerGraph()

    # Create nodes
    gen = graph.spawn('gen', label='Generator')
    gen['volts'] = 240
    gen['amps'] = 25  # 25A generator
    gen['live'] = True

    breaker = graph.spawn('breaker', label='Breaker')
    breaker['ratingAmps'] = 15  # Only rated for 15A

    load1 = graph.spawn('load', label='Load 1')
    load1['watts'] = 2000  # 8.3A

    load2 = graph.spawn('load', label='Load 2')
    load2['watts'] = 1500  # 6.25A (total would be 14.53A - still OK)

    # Wire them
    graph.connect(gen, 0, breaker, 0)
    graph.connect(breaker, 0, load1, 0)
    graph.connect(breaker, 0, load2, 0)

    print("Configuration:")
    print(f"  Generator: 240V @ 25A")
    print(f"  Breaker rating: 15A")
    print(f"  Load 1: 2000W (8.3A required)")
    print(f"  Load 2: 1500W (6.25A required)")
    print(f"  Total: 14.53A (within breaker rating)")
    print()
    print("Running simulation for 3 seconds...")
    print()

    tick_count = [0]

    def log_state():
        tick_count[0] += 1
        if tick_count[0] % 30 == 0:  # Print every ~3 frames at 10 fps
            gen_state = gen['state']
            breaker_state = breaker['state']
            draw = gen['drawAmps']
            print(f"  Gen: {gen_state:8} | Breaker: {breaker_state:8} | "
                  f"Draw: {draw:.2f}A")

    # Hook into tick loop
    import time
    original_run = graph.run

    async def logged_run(duration, fps):
        graph._running = True
        graph._target_fps = fps
        graph._last_tick_time = None

        start = time.time()
        while time.time() - start < duration and graph._running:
            await graph._tick_loop()
            log_state()

    graph.run = logged_run

    await graph.run(duration=3, fps=10)

    print()
    print(f"Final breaker state: {breaker['state']}")
    print()


if __name__ == '__main__':
    print()
    print("Python Power Graph System - Examples")
    print("=" * 70)
    print()

    try:
        asyncio.run(main())
        asyncio.run(test_overcurrent())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
