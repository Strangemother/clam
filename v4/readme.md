

> Monkier for this segment of work is the "Brain Wave Bloom".


+ Brain: Befit the pattern of a "brain" with segments of work and task isolated between messaging path
+ Wave: Sequeunces of information flow from outward to inward, association of connections are wave-like in the activation
+ Bloom: fractal-like expansion of ideas and thoughts, branching in a non-linear fashion. Unfolding of layer connection yields smaller intricate layers for meta flourishes.


V4 Contains more audio receiver features. And the better slotting as per v3 notes.


## Setups

### UI (Django)

run the django site within `site`

    activate.bat
    cd site
    run_dev.bat

Navigate to:

    http://localhost:8006/home/

### Proxy Server (Websockets)

Run the `primary` within a new console.

If the env is active, the `run_proxy.bat` does the required steps:

    activate.bat
    cd primary
    run_dev.bat

This opens a websocket server port:

    ws://localhost:8765/


---

## Process

Fundamentally all messages are fed into the clustering system. Each message is _from_ somewhere, and has a _destination_ built into the cluster graph.

The cluster farms messages to the correct connect clients - coded as-required.


    user connects:
        first message (automatic): `recv_new_socket`
            + provide/get ID
            + register client
            + tell cluster: `cluster.new_socket`
        sends message:
            `cluster.recv_message`
        disconnects:
            `clients.drop_register`

The next steps are applied within the cluster, farming messages to configured clients.

---

## Modules (Abilties)

Units connect to the cluster (aka mesh graph) with an ID and abilties, such as "memory". This client receives websocket messages to work-on. The response from this client is fed back through the mesh graph.

The Module here doesn't really care about the routing (unless built to do so.)

### Naming

It seems prudent to stack this mesh accoring to the brain (it's what I'm trying to mimic) - In a hopes I will name modules correctly for their function.


### Thalamus

The routing unit, receiving messages and sending them to the correct first steps.

    https://en.wikipedia.org/wiki/Thalamus
    https://www.ncbi.nlm.nih.gov/books/NBK542184/

This Thalamus exists within the Diencephalon

    https://en.wikipedia.org/wiki/Diencephalon

---

In stage 1, the thalamus can recieve messages from the user input, and perform prelinimary dispatch.

The Thalamus connections in the mesh:

    user_message => thalamus

User message is recieved through the non-unit client (it's considered special).



## Updates

+ UI: Sends and receives websocket comms - mostly copied from v3.
+ proxies: A "primary" slottable websocket server, waiting for modules

