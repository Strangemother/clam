# Func Pipes V2


## Architecture documentation

The Python-owned graph direction, UI ownership boundary, command/event
protocol, and implementation plan are documented in [docs/README.md](docs/README.md).


## Update

It works great. This second version is agnostic to flow and nodes.

creating a node:

1. Create a node template `templates/nodes/simple-cell.html`
2. Create the JS node `js/prompting/nodes/simple-cell`
3. Add to available node list in python `NODES += [ ("simple-cell", "Simple Cell") ]`


---

The first version works well, but after using the AI, I regret it and tend to strip back and start again, focusing on the improvements and gaps.

+ DragSolo manages mouse node dragging
+ ZoomableInfiniteDrag manages space zooming and panning
+ Vue handles panel spawning


Lessons:

- Pseudo Graphs - every node is ethereal, every edge is transient.
- The graph event machine moves events node to node, through edges

Therefore for JS focus, this is a event to event caller managed by a single event loop.

1. Node emits event
2. event is stacked
3. graph reader gathers dests
4. graph reader calls each dest
4. Node(s) emit events

A node is ethereal, thus a default pushes edge to edge (psuedo node / default node)
A node function retuns a value, the node emits an outbound event.
If the event destination is unedefined, we call the the default edge.

This default edge is an event spout. Emitting the same event as a Edge emission.

---

Fundmentally it's psuedo nodes through pseudo edges. A real edge or real node can be applied late.

```js
function myFunc(value) {
    return value + 1
}

graph.add('myFunc', myFunc)

graph.connect('loadedFunc', 'myFunc') // build edge.
```


