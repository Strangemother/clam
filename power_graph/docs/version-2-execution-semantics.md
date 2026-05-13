# Power Graph Version 2: Execution Semantics

This document is a companion to version-2.md.

Its purpose is to define how the runtime executes, not just what concepts exist.
The goal is a close representation of physical circuits without becoming a full circuit solver. The public model can keep a simplified Power unit, while event flow, ordering, loss, and feedback behave in a more realistic way.

## Design Target

The runtime should feel electrically believable in these ways:

- supply persists until interrupted
- demand travels upstream rather than appearing magically at the source
- losses and impedance belong to wires and components
- multiple sources do not merge by race condition
- disabled nodes become electrically quiet
- feedback and fault effects travel through the graph in a deterministic order

The runtime is not trying to be SPICE. It is a deterministic approximation for a game simulation.

## Core Model

The gameplay-facing quantity remains a simplified Power value and unit.
To make event flow behave more like a real circuit, each in-flight power event also carries derived transport fields:

- power: the gameplay energy rate or quantity being offered, requested, stored, or consumed
- potential: a voltage-like pressure used for brownout, compatibility, and directional flow
- current_limit: a current-like capacity used for sharing, saturation, and overload
- phase: optional ripple or oscillation phase owned by the emitting node
- impedance_sum: accumulated path cost through edges and components

This gives the runtime enough structure to behave plausibly without requiring a full analog solve.

## Event Kinds

The bus carries four distinct kinds of events.

### 1. SupplyState

- Direction: downstream by default
- Lifetime: sticky
- Purpose: a source or intermediate node offers continuing power until changed or withdrawn

This is the closest equivalent to a live wire remaining energised.

### 2. PowerRequest

- Direction: upstream by default
- Lifetime: sticky with expiry
- Purpose: a sink or intermediate node requests power from reachable sources

Requests must not live forever. Each request carries:

- request_id
- origin_node_id
- created_tick
- expires_after_ticks
- requested_power
- requested_potential range or class

If the requester disappears, disables, or stops asking, the request is withdrawn immediately. If no refresh occurs before expiry, it is removed automatically.

### 3. FeedbackPulse

- Direction: usually upstream, but may be either direction
- Lifetime: transient
- Purpose: ripple, fault response, back EMF style effects, local transients, and short-lived control reactions

FeedbackPulse exists for one settle pass unless re-emitted. It is not sticky by default.

### 4. Action

- Direction: injected from outside the graph
- Lifetime: one-shot
- Purpose: player interaction, repair, toggle, websocket control, remote automation, scripted events

Actions do not mutate the graph mid-pass. They are queued and applied at the start of the next world tick.

## Deterministic Tick Contract

Every world tick executes in fixed phases.
This is the main rule that keeps the simulation stable and testable.

### Phase 0: Apply queued actions

- Drain the external command queue in FIFO order.
- Apply mutations before any simulation work for that tick.
- Topology changes, toggles, resets, and remote commands all happen here.

This matches the current runner contract and should remain true.

### Phase 1: Build the active frontier

- Collect all sticky SupplyState and PowerRequest events that survived from the previous tick.
- Drop expired requests.
- Remove any event whose owner node or edge is detached or disabled.
- Freeze a read-only snapshot of node state, edge state, and active sticky events for the first settle pass.

### Phase 2: Settle the graph

Each world tick performs a bounded number of settle passes.
These passes represent the graph finding a stable electrical state at the current instant, not extra elapsed time.

Recommended defaults:

- min passes: 1
- typical passes: 3 to 6
- max passes: 8 to 16
- stop early if all material deltas are below epsilon

Each settle pass runs this loop:

1. Deliver inbound events from the previous pass snapshot.
2. Let each enabled node compute from that snapshot only.
3. Emit candidate SupplyState, PowerRequest, and FeedbackPulse outputs into a next-pass buffer.
4. Transport those outputs through edges, applying loss, impedance, filtering, and direction rules.
5. Merge results deterministically.
6. If no node output changed materially, stop settling early.

Nodes do not recursively mutate each other immediately during the same pass.
They read from the current snapshot and write to the next buffer. This avoids timing races and makes loops tractable.

### Phase 3: Commit the settled state

- Promote the final settled sticky events to the active runtime state.
- Commit node internal state changes.
- Clear transient FeedbackPulse queues.
- Publish external observations, telemetry, and UI events.

### Phase 4: Integrate time-based state

After the graph is electrically settled for the tick, integrate elapsed time `dt` into timeful storage and work:

- batteries charge or discharge
- heaters warm or cool
- capacitors accumulate or release energy
- clocks and oscillators advance phase
- wear, overload timers, and fuse heating update

Important: settle passes solve instantaneous connectivity for the current tick; only the outer world tick advances time.

## Node Contract

Each node is responsible for its own local solve.
For every settle pass it receives:

- inbound SupplyState events by input port
- inbound PowerRequest events by input port
- transient FeedbackPulse events
- its own internal state snapshot
- the current tick id and settle pass index

Each node returns:

- updated internal state proposal
- zero or more downstream SupplyState events
- zero or more upstream PowerRequest events
- zero or more FeedbackPulse events
- optional fault or telemetry events

Node logic should be pure for the duration of one settle pass: same inputs, same outputs.
State becomes real only at commit time.

## Source, Sink, and Storage Semantics

### Sources

- advertise a sticky SupplyState while able to provide energy
- may reduce potential or current_limit under load
- may sag, trip, or shut down when protection rules trigger

### Sinks

- emit PowerRequest while they need power
- accept partial fulfillment
- enter brownout, idle, or off states depending on delivered potential and power

### Storage nodes

- may emit requests while charging
- may emit supply while discharging
- must not charge and discharge the same capacity bucket in the same commit step unless explicitly modelling separate paths

## Realistic-Enough Merge Rules

The runtime should not choose supply by who responds first.
That is a scheduling artifact, not circuit behaviour.

Use deterministic merge rules instead.

### Requests

When multiple upstream paths can satisfy a request, sort candidate paths by:

1. lowest impedance_sum
2. lowest hop count
3. lowest source node id
4. lowest edge key in lexical order

This gives a stable answer across runs.

### Compatible supplies

Supplies may combine when they are electrically compatible by node policy.
For the simplified model, compatibility means all of the following are true:

- potential is within the node's accepted tolerance band
- source classes are allowed to parallel each other
- polarity or direction agrees

When compatible supplies combine:

- effective potential is determined by the dominant rail or weighted average defined by the receiving node class
- current_limit sums across compatible parallel sources
- delivered power is capped by both source capacity and downstream demand

### Incompatible supplies

If supplies are incompatible, the node or protection layer must choose one of these behaviours explicitly:

- isolate one source and reject the others
- raise a fault or overload event
- trip a protective node
- refuse the merge and expose no output

The runtime must never silently merge incompatible sources.

## Edge Semantics

Edges are part of the solve, not just topology.
Every traversed edge may apply:

- resistance or transmission loss
- maximum current or throughput
- filtering or damping of ripple phase
- propagation delay in ticks, if needed for special links
- one-way or two-way direction rules

Edges should own their runtime transport state through the graph-level edge store. Node-local caches must not become the source of truth for wire behaviour.

## Directionality and Feedback

Power usually travels downstream as SupplyState.
Demand usually travels upstream as PowerRequest.
FeedbackPulse may travel either direction.

This gives a close-to-physical pattern:

- sources energise reachable networks
- sinks ask for current draw and work budget
- the network returns local transient consequences upstream and sideways through subsequent settle passes

FeedbackPulse should be additive and brief. It is used to model transient effects, not steady supply.

## Disabled, Detached, and Internal On-Off

These states must stay separate.

### Detached

- not in the graph
- no event ownership
- no electrical participation

### Disabled

- still exists in the graph
- ignores inbound events for simulation purposes
- emits a single withdrawal of any previously sticky outputs
- becomes electrically quiet after that withdrawal

Disabled nodes must not keep re-emitting `None` or any other output every tick.
One off-transition is enough, then silence.

### Internal on-off or running state

- belongs to the node itself
- used for batteries, heaters, switches, converters, machines, and damaged devices
- may change whether the node emits or requests power while the graph connection remains enabled

## Brownout, Sag, Trip, and Protection

Protection behaviour is where the game-friendly approximation should feel most realistic.

- low potential causes brownout before hard off when the node supports degraded operation
- excess requested current or sustained overload causes sag, heating, or trip depending on the device
- trips are latched state changes until reset
- fuses and breakers are modelled as nodes or edge protection elements, not hidden side effects

The important invariant is conservation-like behaviour:

- delivered power cannot exceed available source capacity minus losses
- protection events may reduce delivery further
- no merge rule may create extra energy during settling

## Ripple and Oscillation

Ripple is best represented as a stable property of the emitting node, not as a brand new event storm every frame.

Recommended model:

- sticky SupplyState may include phase, amplitude, and frequency metadata
- source nodes own phase advancement during the outer tick
- receiving nodes sample the current phase during settling
- edges may damp or delay ripple

This keeps oscillation believable without flooding the event bus.

## Multi-Graph and Bridge Semantics

Independent graphs may run on separate clocks, but bridges must be explicit.

- same-clock bridge: forwards during the same world tick using the same settle contract
- cross-process or websocket bridge: forwards with at least one tick of latency unless explicitly configured otherwise
- remote actions still enter the Action queue and apply at Phase 0 of the receiving graph

This prevents hidden mid-tick mutation from network timing.

## Persistence Contract

To restore a running graph faithfully, save more than topology.

Minimum save set:

- node configuration
- node internal state
- edge configuration and runtime edge state
- active sticky SupplyState events
- active sticky PowerRequest events with remaining expiry
- tick counter
- deterministic ripple phase and random seeds if used

Optional exact-replay save set:

- current settle pass index
- in-flight next-pass frontier buffers
- pending protection timers and transient pulse queues

If exact replay is not required, transient FeedbackPulse data may be dropped on save and rebuilt over the next tick. Sticky state must be preserved.

## Ordering Guarantees

The runtime should guarantee all of the following:

- same graph state plus same inputs yields same result
- queued actions are applied before the tick they land in
- node iteration order is stable
- tie breaks do not depend on network latency or dictionary ordering
- disabled nodes stay electrically quiet after their off transition

## Suggested Event Schema

This is intentionally compact.

```python
Event = {
	'id': str,
	'kind': 'supply' | 'request' | 'feedback' | 'action',
	'owner': int,
	'port': int,
	'direction': 'downstream' | 'upstream' | 'local',
	'power': {'value': float, 'unit': str},
	'potential': float | None,
	'current_limit': float | None,
	'phase': {'offset': float, 'frequency': float, 'amplitude': float} | None,
	'path': [str],
	'impedance_sum': float,
	'created_tick': int,
	'expires_after_ticks': int | None,
	'sticky': bool,
	'meta': dict,
}
```

The exact field names can change. The important part is identity, deterministic ordering, direction, expiry, and enough electrical metadata to avoid race-based behaviour.

## Recommended Test Targets

The implementation should have regression tests for:

- same input, same settled result across repeated runs
- disabled node emits one withdrawal then stays quiet
- command queue mutations apply before the next tick
- request expiry removes stale demand
- two equal paths resolve by deterministic tie break, not response timing
- compatible parallel supplies share load
- incompatible supplies trip, isolate, or refuse to merge predictably
- save and reload preserves sticky energised state
- bounded settle passes converge or fail loudly

## Practical Interpretation

The runtime should behave like a deterministic event-driven approximation of circuit flow:

- sticky supply models energised conductors
- sticky requests model demand pulling from upstream
- transient feedback models ripple and short-lived reactions
- bounded settle passes model the graph reaching a stable state for the current instant
- outer ticks model real time and energy integration

That is close enough to physical circuits to feel coherent, while remaining cheap enough for a game runtime.
