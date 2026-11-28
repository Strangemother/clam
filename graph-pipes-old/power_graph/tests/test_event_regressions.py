import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from power_graph import PowerGraph
from power_graph.event_system import EventEmitter, EventMonitor
from power_graph.node_base import NodeBase
from power_graph.runner import GraphRunner


def _make_runner() -> GraphRunner:
    runner = GraphRunner.__new__(GraphRunner)
    runner.fps = 20
    runner._dt = 1.0 / 20
    runner._queue = asyncio.Queue()
    runner._running = False
    runner._tick_subscribers = []
    runner.graph = PowerGraph()
    return runner


def test_once_listeners_do_not_skip_peers():
    emitter = EventEmitter()
    calls = []

    emitter.once('demo', lambda event: calls.append('first'))
    emitter.once('demo', lambda event: calls.append('second'))

    emitter.emit('demo')

    assert calls == ['first', 'second']


def test_event_monitor_tracks_emitted_events():
    emitter = EventEmitter()
    monitor = EventMonitor(emitter)

    emitter.emit('graph:start', label='graph')
    emitter.emit('graph:stop', label='graph')

    stats = monitor.get_stats()
    assert stats['total_events'] == 2
    assert stats['event_counts'] == {'graph:start': 1, 'graph:stop': 1}
    assert stats['events_per_second'] > 0
    assert stats['bytes_per_second'] > 0


def test_graph_dispatch_state_is_isolated_per_graph():
    graph_a = PowerGraph()
    graph_b = PowerGraph()
    panel_a = graph_a.spawn('load')
    panel_b = graph_b.spawn('load')

    NodeBase.dispatch(panel_a, 'test:event', {'graph': 'a'})
    NodeBase.dispatch(panel_b, 'test:event', {'graph': 'b'})

    events_a = [event.data for event in graph_a.emitter.get_log() if event.type == 'test:event']
    events_b = [event.data for event in graph_b.emitter.get_log() if event.type == 'test:event']

    assert events_a == [{'graph': 'a'}]
    assert events_b == [{'graph': 'b'}]


def test_multi_output_sources_accumulate_by_pip():
    graph = PowerGraph()
    gen = graph.spawn('gen')
    bus = graph.spawn('bus-bar', preset={'outputCount': 2, 'weights': [1, 1]})
    load = graph.spawn('load')

    graph.connect(gen, 0, bus, 0)
    graph.connect(bus, 0, load, 0)
    graph.connect(bus, 1, load, 0)

    gen['live'] = True
    gen['volts'] = 240
    gen['amps'] = 10
    graph.emit(gen, {'v': 240, 'a': 10})

    assert load['powerSources'] == {
        '2:0': {'v': 240.0, 'a': 5.0},
        '2:1': {'v': 240.0, 'a': 5.0},
    }
    assert load['signal'] == {'v': 240.0, 'a': 10.0}


def test_runner_remove_cleans_connections_and_state():
    runner = _make_runner()
    gen = runner.graph.spawn('gen')
    load = runner.graph.spawn('load')
    runner.graph.connect(gen, 0, load, 0)

    gen['live'] = True
    gen['volts'] = 240
    gen['amps'] = 10
    runner.graph.emit(gen, {'v': 240, 'a': 10})
    assert load['state'] == 'on'

    runner._apply({'op': 'remove', 'id': gen['id']})

    assert runner.graph._find_panel(gen['id']) is None
    assert runner.graph._connections == {}
    assert load['signal'] is None
    assert load['state'] == 'off'


def test_tick_subscribers_receive_detached_snapshots():
    runner = _make_runner()
    load = runner.graph.spawn('load', label='Original')
    seen = []

    def mutate_snapshot(panels):
        panels[0]['label'] = 'Mutated'
        seen.append(panels[0]['label'])

    runner.subscribe(mutate_snapshot)
    runner.tick_once()

    assert seen == ['Mutated']
    assert load['label'] == 'Original'


def test_repropagate_does_not_revive_tripped_generator():
    graph = PowerGraph()
    gen = graph.spawn('gen', label='Gen', preset={'volts': 240, 'amps': 10})
    load = graph.spawn('load', label='Load', preset={'watts': 4000})

    gen['live'] = True
    graph.connect(gen, 0, load, 0)
    graph.repropagate_all()
    graph.update_all_gen_draws()

    assert gen['state'] == 'tripped'
    assert load['state'] == 'off'

    graph.repropagate_all()

    assert gen['state'] == 'tripped'
    assert load['state'] == 'off'
    assert load['signal'] is None


def test_disabled_converter_stays_quiet_on_tick():
    graph = PowerGraph()
    gen = graph.spawn('gen', preset={'volts': 240, 'amps': 20})
    conv = graph.spawn('converter', preset={'outVolts': 48, 'efficiency': 0.9})
    load = graph.spawn(
        'load',
        preset={'watts': 150, 'minVolts': 38, 'brownoutVolts': 44, 'maxVolts': 60},
    )

    graph.connect(gen, 0, conv, 0)
    graph.connect(conv, 0, load, 0)

    gen['live'] = True
    graph.repropagate_all()

    conv['enabled'] = False
    graph.repropagate_all()

    gen['ripple']['enabled'] = True
    gen['ripple']['interval'] = 0
    conv['ripple']['enabled'] = True
    conv['ripple']['interval'] = 0
    graph.emitter.clear_log()

    graph.tick(1.0 / 20)

    converter_events = [
        event for event in graph.emitter.get_log()
        if event.type == 'graph:emit' and event.label == f"panel-{conv['id']}"
    ]

    assert converter_events == []
    assert conv['state'] == 'off'
    assert load['state'] == 'off'
    assert load['signal'] is None


def test_brownout_load_counts_toward_battery_draw():
    graph = PowerGraph()
    battery = graph.spawn(
        'series-battery',
        preset={'volts': 12, 'amps': 10, 'chargeAmps': 0, 'capacityWh': 20, 'chargeWh': 20},
    )
    load = graph.spawn(
        'load',
        preset={'watts': 240, 'minVolts': 8, 'brownoutVolts': 18, 'maxVolts': 60},
    )

    graph.connect(battery, 0, load, 0)
    graph.repropagate_all()
    graph.update_all_gen_draws()

    assert battery['state'] == 'discharging'
    assert load['state'] == 'brownout'
    assert load['current_watts'] > 0
    assert battery['drawWatts'] == round(load['current_watts'], 1)