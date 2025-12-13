# V3

In the second draft we successfully arranged a suite of models, interacting through their own conversation, pumping messages to the user _ad-hoc_. With this action the model can interject with thoughts, but we discovered we can essentially _hot program_ the LLM from input data using hidden system events (background messages).


The limit was the centralisation of many bots. Without a mini cluster of GPU's we ran out of resources. So the next trick is to find smaller models, farm to distant GPU's, or build a singular more comprehensive LLM.

_One big bot_ is not an option. As the key feature here is unique distinct tooling per unit (with the capability of programming each unit for _slot-in functionality_).

Therefore smaller bots and a cluster.

voice:

+ Shazam style: Constellation of frequency peaks: python devaju
+ mel freq sepstural coefficients: mfccs
+ prosidy control: Control speech
+ emotion or sentiment analysis
+ TTS


## Notes


### Mutli-mind

Has cross over with

+ Mixture of Experts
+ Chain of thought (decision tree)
+ RAG

An input is given to many smaller (variant) models, expecting similar results.
The _multi-mind_ model collects all results and uses this information as a context base, potentially applying a RAG layer for top level context appliance.

The result is a wider cohesive output of the query resource.

This information can be cross referenced with a _truthy test_ and pushed further.



### Simplified messaging technology

To simplify _distance clustering_ and bridging, the messaging between steps is performed through a chain of throughput, handled by a messaging server.

An _output_ has a destination such as _mind result_ to _memory_. The message origin defines the destination, but the connections are bound through a separate graph.
The distinct connections tree lives outside the modules, and essentially becomes a thin client to client messaging suite.

A language client is assigned to a possible _slottable_ unit. The _internal_ endpoint (e.g. Olloma) connects to its messaging socket. Or more precisly, a websocket client acting as jump host to the internal messaging client.

Message in/out the language model are automatically tagged through the _jump host_

---

For this we can define unique types of client, such as _memory_ or _foreground_. The client connects to the language model and ferrys messages through to the primary.

And client can hear its neighbours messages and react to actions outside its main messaging pipe. e.g. A memory model may _immediately_ switch context upon an _alert_ message.

> As a scenario, the system could be thinking about another routine and the user yells "STOP! Fire!" The forground sends this to the thinker, which serves it to it's _"hot inferences"_ step. This hot inteferences emits an alert to all units, potentially stopping executing modules.


#### Extended

1. A "jumphost" connects to olloma, or a gradia, or some endpoint (streaming or non streaming)
2. A jumphost maintains itself with abilities, e.g. "thinker", "memory", "knowledge" - in the form a self-contained config.
3. the Jumphost registers itself to the primary messaging system
4. The messaging system dispatches to a target (ability)
5. The jumphost receives, processes, emits, waits, returns
6. The primary knows to move this message to the next graphed target.


A jumphost is essentially a self contained messaging unit for one bot or sevice, e.g. olloma, or audio services (many gradio)

This can connect to a host, and its abilities are registered.
A jumphost can potentially register many abilities, and recieve multiple _types_ of message - but it's easier to visual as single instances.

---

The messaging platform is a websocket service, ferrying messages between clients.

Each message is _tagged_ with knowledge, but usually a message destination is pre-determined through the graph connections built into the messaging platform.

As such, a single _unit_ (jumphost or other machinery) may just _connect with abilities_ and perform its singular task on every message. Given the message response will have a graph path to the destination, the handoff is transparent.

---

E.g, A input from the user heads into the messaging layer. Its first destination is applied - and returned. Any content from _first_ heads to _thinkers_. There may be one or more _thinkers_ and they receive a prepared message. There responses appear adhoc in the framework, of which will _wait_ for all, then send the message to the next step e.g. _memory_ And so on...


This is similar to a normal WS messaging framework (e.g. Porthouse) but with a pre-deterined configuration for messages.

---

Because this is websockets, the actions should occur in-parallel.


### Distant clustering

Spread the bots across multiple machines, allowing them to work in a graph of parrallel work.

### Smaller

Smaller, more distinct bots are hitting the market. I've focused on PHI and SMOL models for smaller _heads_, and Llama for _conversation_.


## New

### VAD frontend

For audio clustering a new venture:

1. VAD Algorithm built into the UI (browser)
2. Send to a Whisper TTS with event data (e.g. location)
3. Send to the conversation - with event data.


We can use the VAD tip detection for conversational chunking. like this amazing project: https://github.com/ricky0123/vad

#### Multi monitor mic.

Pop a UI in the phone and in each room, the events can capture _where_ the sound is coming from.

Extras:

+ Using echo cancelling or simple triangulation, we could detect how close.


### Chain of Thought isn't great

Complex but if we create a chain (in the form of single step actions) of tasks, and bridge them using communication pipes, we can gain a continious flow of messages through a graph. Or a "Tree of Thought" (as it's coined now)


### Memory Module

Create a bot with a prompt to specifically generate key thoughts about a user, and the actions

Consider implement the old "who what when where why" algorithm (it'll probably work now).
Then store thin strings for memory.

### Primary bot

After v2 we see _farming_ to sub-bots works great. Next we need an easy method to slot them into the primary (background to primary slotting)


Also - be more specific with its thought offloading. We'll have a primary bot step to consider which bots to use.

---

We'll maintain a realtime index of available _local machines_ - each with the assigned possibilities. e.g "memory bot", "math bot", "know about user bot" etc. Each module _may_ recieve a message from the primary.

This is part of the primary bot management. Psuedo prompt:

    With this message, identify the best available bot given its designation and purposes relative to the user input.


Importantly these sub-bots are mostly considered persistent. E.g. the primary always knows it can rely on 'memory' through a session.

Additional bots can be applied when the context considered it.

    if required load any of: code, math, conversation, timer

like a function caller


### Function calling

Consider fine-tuning a small LLM to respond with a specific function set.



## Dr Bot

Oooo such a lovely idea I've always wanted to implement.

The doctor bot lives _above_ the primary here. Essentially a more refined goverance machine. Its sole purpose is to override the functionality of the primary, as a guard and arbitor.

It ensures primary is acting as expected. And when rouge, can press the reset button or stop an inference. This implies is maintains a keen overhead for all IO.

Fundamentally all messages through all sub bots are sent to the Dr Bot in realtime.
If the dr senses a poor response or action, it will interject the forward context (the conversation machine) and block the output.

This will occur mid-stream, as the dr received the same information as the forward, however as the forward is communicating, the Dr is evaluating and considering a stop command.

In audio state, there's a new bot with altered voice.
For 'agency' over the primary, there will be a function caller for the dr.


At any time the user invokes the dr through _asking_ for a superior.

> Literally 10 years ago I wrote this concept down. It's pretty much given we have guard rails. In this case the guard rail is a slow methodical thinker, designed to step in at the last moment


A user should be able to state "Doctor bot, is this action correct" It will enforce a response.

---


It can and **will** communicate to the primary context in _person to person_ mode.


    Dr: This is the doctor. You output is subject to scrutiny, define your reasoning.
    Primary: My objective is to check the correct result for this input ...
    Dr: The defined content is refused.

Alternatively:

    User: Doctor please validate the upstate of the primary
    Dr: Validating... Enabling. "Primary this is the Doctor please state your initial context..."
    Primary: "My initial context is to provide helpful answers to the user..."


Notably there must be a strategy to intertwine the verification steps of the dr and the primary. I feel system prompt inject is not enough. potentially a regraphing of the sub bots with a command feature for the primary.

... Else the primary may never agree with the dr.