

I've had a better thought. And some better tech.

A concurrent thinking bot needs a persistent feed. So this version will be

+ Memory bot
    Receive thoughts to store forever
+ Sleeping service
    The bot will _sleep_ for long periods, thinking and memorizing on all thoughts as a collective narrative.
+ background bot
    the fore-cortext, ferrying messages between nodes
+ sub thought space

+ frontend bot
    To chat with person

The goal is a more real, private, personal bot, reactive to the conversation and the meta data around it.


---

## Memory Bot

+ at an endpoint
+ produces dated 'memories' for later retrieval
+ has access to a _history_ of knowledge
+ Creates memories as _files_

Memories are both active and background.

A memory should be pushed into the context. Allowing live messaging to occur from a system message.

We can perform this through a sqlite db, with a _write sentences_ as memories.
When the background bot performs actions, these sentences exist as thoughts.

Therefore we can push active messaging, such as "I notice this link you've just sent to github"

Messages are more rigid, with a prompt context, and instructions. The memory is not pure - meaning the stored value will contain meta data. E.g. a  memory _file_ will include the date and time.


---

## Sleep service

+ At an endpoint
+ manipulates long term, RAG, finetune, edit memories
+ Can _add_ and _Remove_ knowledge
+ can _edit_ and _amend_ knowledge

This is designed to be long term training downtime. Editing its own memories and performing long term data crunching.

During sleep, we load a high temperature model with long context and a heavy thinker.

+ Load from today memories
+ knowledge from the past
+ "background" thoughts
    + previously dismissed/ignores
    + thinking messages,
    + stuff to think about _later_ (future parked throughts)
    + internal memories - a _sub concious_ for lack of a better term
        + memories for keeping tuning in the right direction
        + memories and knowledge saved from previous sleeps
        + generally, messages not seen in the chat service - an internal ego.

The sleep _thinks hard_ and will use enough GPU for it to be sleepy. Breaking training may yield a messy wake up - best leave it to sleep.

---

## background bot

+ An endpoint and primary context loop maintainer.
+ Pushes messages, holds conversation timers
+ can access memories and knowledge for the _sub thought_ space.

## sub thought space

The sub thought space, or (lacking definitions) a sub concious area, is the thought space to manage background decisions and message positions, and under-thoughts.

In a case where the background clock _ticks_ and should ask the user a question. the sub thought space is _asked_ for the response, where a prompt is given e.g. "The user has not responded for 17 minutes, given the history, consider and return a response."

The background space returns the result and sends it to the user.

## Foreground

It's a chatty bot.

## User Knowledge.

Gather and understand knowledge statements of the user, e.g. name, age, favourite food.
These are stacked as user based information. A graph of user persona


## Lifetime cache

some information is needed for self awareness, such as age, current datetime,
a list of concurrent tasks

These can exist in a lifetime cache, bank for read/write,

## Persona

a persona persists for the character. This mainly exists in the foreground as the chatty bot interface but also includes _name_ and personal choices.

This should manifest organically

### Name

One of the first persona elements is likely a name. Initially this is undefined and the bot prompt will know this.
Through initial conversation the topic of a name should be raised. However it would be interesting to see if we can code the bot to choose a name over a period.

### Emotive State

Give the state of information the persona will have an emotive state. In a crude form this can be a _happiness_ or _anger_.

### Identity

The bot should think in first person, talking to the user as the operator



---

# Requirements

Using the non-stream version for now.

+ GET POST Routines
+ The background loop and clock
+ templatable prompt files
+ A memory input routine for sqlite memories.



