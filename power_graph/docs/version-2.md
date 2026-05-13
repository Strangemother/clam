# Power Graph Version 2

Learning from the existing versions, the next version:

- All nodes have power ripple
- a node is a general sink or source of power. Everything acts like this.
- Nodes can have multiple inputs and outputs
- multiple graphs, both parallel, and inline (subgraphs)
- The graph runs in both directions. Power tends _down_, ripples and feedback tends up.

---

The new version should mimic the js runtime allowing a event bus to ferry changes through the edges.
To simplify, this version is focused on power

- Power is an energy (Class). It has a value, and a unit. It can be converted to other units.
- Nodes can emit power, and receive power. They can also have internal state that changes how they emit or receive power.

When nodes perform work they either consume power, or produce power. Depending upon configuration, they may do both. For example, a heater consumes power, and produces heat. A solar panel produces power, but does not consume power. A battery can consume power to charge, and produce power when discharging.

To perform this cleanly a Node manages its own emissions.

- A node returns events, they're pushed to the event bus.
- The event bus performs a cycle, collect and moving to the next node inbound.
- If the target nodes is missing or disabled, the event is dropped or used elsewhere.

Multiple inputs may supply power to a node. With an event bus, the node can react to each input independently. 
The bus can iterate and push multuple events to the same node, and the node can react to each event separately.
This allows combination of downstream power.

---

### Ripple, Backpropagation, and Feedback

Ripple is the concept of power flowing through the graph. When a node emits power, it creates a ripple that flows through the graph. The ripple can be thought of as a wave that propagates through the graph, affecting all downstream nodes.

To apply this neatly ripples will _backpropagate_ through the loop. This means an event is applies _in reverse_ as feedback. 
Power events are applied to the event bus, with a simple flag to go upstream.
The power event is applied to the node, and then the bus iterates upstream, applying the event to each node in reverse.

Simultaneously the bus is pushing events downstream. When the bus applies power changes to a node, they'll accumulate in the single cycle. therefore a node sends and receives in a single stroke.

1. On _work_ a node emits upstream and/or downstream Feedback (reverse events) 
2. The event heads to the previous nodes and pushes them onto a _feedback queue_.
3. Said node will process its _work_, receiving power and feedback, emitting power and feedback.


### Events on Change

Although "power" is concurrent, this runtime doesn't emit `Power` per node per cycle by default. Instead, sent power is assume _constant until change". Meaning a node emits one event at the start of a power delta, and a second event to close. The time between is assumed to be a constant power.

Notably ripples will change frequently. This is tackled through either:

1. Allow the feedback to emit every node on every cycle - however this will be very noisy
2. Emit power; with an attached phase or _ripple_. The ripple value is computed by the owning node, ensuring only one event is needed for an unlimited ripple event. 

---

consideration:

To simplify the request of power and act a lot like real wires.

When a node requests power, a `PowerRequest` event is emitted upstream. This event contains the amount of power requested, and the unit. The event bus then propagates this request upstream, allowing nodes to respond with `PowerSupply` events. This creates a more dynamic and interactive graph, where nodes can request power as needed, and supply power based on their own internal state and the requests they receive.

As a PowerRequest event propagates upstream, nodes can choose to fulfill the request, partially fulfill it, or ignore it. 
In addition power may fork through two upstream nodes. When this occurs the shortest path to a source wins. If two paths are equal, the first to respond wins. If multiple sources respond, the power is combined (using a voltage/ampere model) and the request is fulfilled by multiple sources.

Because events are sticky, the PowerRequest event will remain active until another request removes it. 



### Enabling and Disabling Nodes

Naming states for a runtime node:

- detached: not part of the graph, not receiving or emitting power
- disabled (state): connected to the graph, but edges are ignored. Essentially the node does not exist.
- enabled (state): connected to the graph, and edges are active. The node functions

Above this runtime implementation, the game state utilises:

- State: if disabled it's not connected - In game object without function
- Enabled: connected to the graph - in game and functioning

For passive objects on the graph (e.g a piece of metal) the state is enough. For complex objects (e.g a battery or heater), they maintain a internal node state for "on".

As an example, for a blown fuse, the node must be _disabled_ but not detached, then the user can _reset_ it (internally) then re-enable it. this simulates the real world process of hardware detachment, repair, and reattachment.

Notably we could just detach the node or alter edges.


### Tick Rate and Time

All nodes should execute their function at a given time. The node must be called at a regular interval. This may occur forcefully through a global even bus tick, or through a self-sustaining ripple. For example, a clock node may emit power on a regular interval, creating its own ripple. 


### Node Connectivity

A node represents a physical object in the game world. It has a position and action. Therefore it may be connected to a remote runtime function, such as a websocket unit, or another process. This is possible through the event bus as presented in the existing working example. Where an event such as `Action` is given to manipulate node data and make live changes. 
Actions _into_ the graph are applied through a queue, pushing into the event bus. Similarly, actions _out_ of the event loop are easily spyable through queues, event buses or literal Node methods. 


### Edges (Wires)

Graph edges are the psuedo physical wires that connect nodes, allowing power and feedback to flow between them.
They have their own partial state and compute. Fundmenally they're a function that alters the applied Power running through.

Typically a wire is multi-directional, and contains lossy functions based on distance, material, and other factors.
In game this is coupled with the visual representation of the wire.


### Saving state

The typical graph and connections are saved as a JSON. However the _executing runtime_ is not part of this. 
The save state information is a capture of the concurrent events within the bus. Upon reload the bus is rehydrated with the same events, allowing the graph to continue with ever seeing a pause. 


### Synopis

With this a node becomes a very simple "energy sink or source" with a python function.
given the event bus ferries power events, the complex part is the power consumption function, to merge input events, ripple, and internal state.

It has:

    Input:
        - Concurrent Power events
        - Feedback events
    Output:
        - Power events
        - Feedback events
    Internal:
        - Capacitance
        - Work Power cost
        - outbound draw

Assuming all expected events are given on a single cycle the node uses these to compute. Mimicing real-world electronics

1. Compute total input power, and feedback
    - These Power events either occur now, or use the previous.
    - Power may already have builtin ripple
    - Feedback will be an additive to the existing power - therefore Power is constant, feedback is fleeting and moves-on
2. Compute work power cost, and internal state changes
    - If required, we re-charge the internal state from the input powers (including immediate ripple)
    - Node performs its own work. E.g a heater heats up, a battery charges, or does nothing (e.g. a busbar)
    - this updates the amount of Power available to emit.
3. Compute output power, and feedback
    - Work is done, we have output power, and feedback to emit. 
    - This step determines the final power and feedback values that will be sent out.
4. Emit output power and feedback
    - Fire and forget. The event bus will handle the rest. 


