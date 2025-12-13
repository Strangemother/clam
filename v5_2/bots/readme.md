# Bots and Mesh Tools

This directory contains the range of "bots" and other tools, designed to _run_
for tooling on the mesh

---

The directory is called "bots/" as a general convenient location, but the location
isn't important - "bots" can run anywhere.


## Bot

A single bot is designed to do the following:

1. Host a http service
2. send and receive mesh messages
3. Comminicate to an LLM


## Tools

A Tool provides additional features on the mesh, not strictly a _bot_ to run LLM
commands. The tools can be used by the bots, store content, and perform background
work, such as a clock ticker.

1. Host or connect to the mesh
2. Send messages across the net.


# Running

A bot or tool runs indpendently, communicating over the mesh. In this current
form _bots_ are runnable modules.


```py
python -m  bots.memorybot
# cd root
run.bat bots/memorybot
# executes __main__
```

The root should contain your tooling. The module `memorybot` runs a service, and
loads `clam` library tools.

Scripts will also work


```py
# cd root
python bots/tickclock.py
```