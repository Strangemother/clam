# Pipe view.


A point to point graph of windows.

1. draggable divs.
2. HTML Content
3. Pull Points

Each panel has input and output nodes.

### Panel

A Panel is a window.js div. Has:

- header
- content
- tips
- locality.


## Nodes

A panel has pips as input or output nodes. By default _one_.
A node is connected to another using a line.

Considering an output, a many edges may connect to one node, and therefore messages are sent parallel.

Multiple pips can run in index, waiting for the first to resolve.

    [] ->

    ---

    [] ->
       ->

    ---

    [] ->
       ->
    [] ->

Same with input.


## Lines

The graph will be a dict, rendered lines with canvas for each point. probably bezier curves because they're easy