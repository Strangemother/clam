# Func Pipes

to run it

    run.bat

Then navigate to something interesting:

+ http://localhost:5001/prompting/

The primary `llm` module accesses an LMSuite endpoint. Ensure to start the server on the target machine.

## Screenshots

Func Pipes is easiest to understand as a set of little graph stories. These are a few of the more characterful ones.

### Talking lightbulb

A light request comes in, a Python function turns it into a bulb command, and a voice node reads the result back like a tiny smart-home scene.

![Talking lightbulb](./HA-talking-lightbulb.PNG)

Used nodes:

- `LLM` (`rgb-light`) turns the user request into a compact light command.
- `Delay` holds or flushes the command so timing can be controlled in the graph.
- `Python Func` calls `simple_bulb_perform`, which bridges into the Home Assistant bulb helper.
- `LLM` (`rgb-light-announcer`) rewrites the result into a short spoken status line.
- `Speak & Play` voices the final confirmation.

### Parallel memory maker

One branch keeps the conversation friendly while the other quietly turns the same exchange into a reusable memory note.

![Parallel memory maker](./parallel-memory-maker.PNG)

Used nodes:

- `Text Input` provides the shared source message.
- `LLM` (`jay / friend.v2`) generates the conversational reply.
- `Sync` buffers multiple upstream messages before releasing them together.
- `LLM` (`jay / memory-m`) extracts a more durable memory-style summary.
- `Display` shows only the latest distilled memory output.

### IndexTTS2 voice chain

This is the fuller voice pipeline: chat text moves into IndexTTS2 with emotion controls, then waits on a generated audio event.

![IndexTTS2 voice chain](./indextts2-voice.PNG)

Used nodes:

- `LLM` (`jay / friend.v2`) produces the line to be spoken.
- `IndexTTS2 Voice` generates speech with reference audio plus vector emotion controls.
- `Voice Result` waits on the returned event id and resolves it into playable audio.

### IndexTTS2 voice result

Same setup, but completed: the event resolves into a playable voice clip you can audition right inside the flow.

![IndexTTS2 voice result](./indextts2-voice-small.PNG)

Used nodes:

- `LLM` sends the final text downstream.
- `IndexTTS2 Voice` emits the generation request and event id.
- `Voice Result` now has the finished clip loaded and ready to play.

### Toasty

A compact character demo for persona work: one prompt, one voice, and a very committed toaster.

![Toasty](./toasty.PNG)

Used nodes:

- `LLM` carries the entire exchange in a single persona-driven chat node.
- The selected prompt/persona keeps Toasty on-theme without extra routing.
- History is enabled, so the character keeps leaning on prior turns.

### Angry bot vs Toasty

A delayed handoff between two personas shows how the graph can stage a reply instead of firing everything at once.

![Angry bot vs Toasty](./angrybot-yells-at-toaster.PNG)

Used nodes:

- `LLM` (`angry-bot`) produces the first side of the exchange.
- `Delay` stages the handoff so the second persona reacts one beat later.
- `LLM` (`toasty`) receives the delayed message and answers in character.

### Persona collision

The same idea pushed further: message history and timing create a weirdly entertaining multi-agent argument.

![Persona collision](./angrybot-yells-at-toaster-2.PNG)

Used nodes:

- `LLM` (`angry-bot`) keeps sending increasingly hostile turns.
- `Delay` acts as the pacing control between agents.
- `LLM` (`toasty`) keeps the counter-persona coherent across a longer back-and-forth.
- History on both sides lets the argument accumulate instead of resetting every turn.
