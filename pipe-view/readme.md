# Pipe view.


![screenshot](screenshot.png)

## Update

It works great:

- Pipes connected through the view, drag drop connections
- zoomable and draggable
- mini wrap of windows with vue js
- Step execution through simple execute/step process.

### UI Choices:

- pipes is a canvas layer drawing node to node
- Zooming is managed independently
- The view is WinBox

I thought winbox would be super useful here (I love it). However I quickly noticed it's more than I need.

In pipes, the x/y is the only focus. Winbox has extras:

- bound X/Y: I would like the infinite drag to plot minus position without caring for winbox locking
- min/max/full (buttons): pipes doesnt need those
    - X/y can be a simple dragging (solodrag)
    - with a CSS handle for width


Note: Some AI was used; I regret it now. I thought it would save me some time.

### next

Now refactored I will implement missing features

- execute highlight: To show what's running.
- back/fore pipe draw swap: The canvas currently runs one layer - we want more than one.
    - and also an animate layer


### Links

- winbox: https://nextapps-de.github.io/winbox/
- petite vue: https://github.com/vuejs/petite-vue

---

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