# Data Flow

This document covers the different ways data can flow through a graph like pipe view.

## Persistent Nodes

Persistent nodes maintain their own data state. They accept input and produce output, but keep a record of their _current_ state.

An example using a simple _adder_ have each node maintain a numer (e.g. 1). When a node receives input, it adds the value to its own state and outputs a new value. 

Without execution the node keeps its state.

## Stateless Nodes

Stateless nodes do not maintain any internal state. They simply take input, perform a transformation, and produce output without retaining any information about previous inputs or outputs.

An example using the same _adder_ would have each node simply with a simple function, or a lambda. When called the result is computed and sent to the output. The node itself maintains no state.


## Stateless Multi tip nodes

Typically we think of nodes as having one input and one output. However nodes can have multiple inputs and outputs, for example a node may have two named inputs (e.g. "x" and "y"). 

As an example we can consider simple logic gates. An AND gate has two inputs and one output. The output is true if both inputs are true, and false otherwise. 

The node itself does not maintain any state, it simply computes the output based on the current inputs.

## Persistent Multi tip 

When a node has multiple inputs, it may need to wait until all inputs have received data before it can produce output. This is often managed through an internal state that tracks which inputs have received data.

For example, consider a node that takes two inputs "x" and "y". The node may maintain an internal state that tracks whether it has received data for both inputs. Once it has received data for both inputs, it can perform a computation (e.g. add the two values together) and produce output.

## Selective Emmissive Nodes

A node may opt to emit outputs for its own coniditions, either on an active path, or through its own selective emission of an output. 

For example, a node may have an internal timer that emits output every second, regardless of whether it has received any input.

### Output "Channels"

A node may have multiple output channels, allowing it to send different types of data to different downstream nodes. For example, a node may have one output channel for numerical data and another for string data.

Currently tips have an integer index, but this can be strings.