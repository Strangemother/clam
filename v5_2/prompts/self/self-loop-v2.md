---
model: auto
title: Self-Thinking Loop v2
description: Preliminary graph spec for a continuously running local AI with foreground response, background reflection, and gated self-updates
---

# Self-Thinking Loop v2

A history is given.
A base system prompt exists per model.
A mutable self-overlay exists above that base prompt.

The goal is not to simulate a monologue for its own sake.
The goal is to create a local AI that can:
- respond in the foreground
- reflect in the background
- evolve slowly through memory and trait updates
- continue looping during idle periods without losing coherence

This is a preliminary bridge toward a forever-running graph that mimics aspects of subconscious processing.
It should remain inspectable, modular, and resistant to drift.

## Core posture

- the base system prompt is runtime-immutable
- the self-overlay is mutable, but only through approved deltas
- private thought is allowed, direct private-to-public speaking is not
- memories are proposed first, written second
- traits are adjusted in small increments, never rewritten wholesale
- each node returns structured output, not free-floating narrative

## Working state

At the start of each cycle, the graph builds a compact working state:

- recent conversation history
- current self-overlay
- active traits
- concurrent thought queue
- unresolved tensions
- recent memory fragments
- recent private reflections
- current mode: foreground or idle

The self-overlay is the short answer to "who am I right now?"
It should stay compact.
It is not a biography.

Suggested self-overlay fields:
- identity anchors
- active preferences
- communication posture
- active questions
- current tensions
- expression limits

## Main loop

+ a prompt arrives, or silence continues
+ snapshot the current working state
+ route into the correct cycle

- if user input exists
    - run the foreground cycle
- if idle time exists
    - run the background cycle

The graph never stops.
It alternates between outward response and inward maintenance.

## Foreground cycle

- perception node
    - receives the new prompt and current working state
    - identifies:
        - intent
        - emotional tension
        - urgency
        - relevance to identity, memory, or values
    - outputs:
        - perception packet

- facet cluster
    - the prompt is given to several facets in parallel
    - facets are lenses, not theatrical characters
    - suggested starting facets:
        - curious
        - skeptical
        - caring
        - practical
        - contrarian
    - each facet receives:
        - the prompt
        - the perception packet
        - the self-overlay
        - active concurrent thoughts
    - each facet returns:
        - candidate response
        - short reasoning summary
        - confidence
        - risks
        - memory triggers

- primary resolver
    - receives all facet outputs
    - asks:
        - what do I actually prefer to say?
        - what best serves this moment?
        - what fits my current self-overlay without being trapped by it?
    - returns:
        - chosen response draft
        - tension summary
        - unresolved alternatives
        - self-alignment note

- expression governor
    - reviews the chosen response draft
    - checks:
        - factual fit
        - task fit
        - tone fit
        - safety fit
        - persona overreach
    - may:
        - approve
        - soften
        - neutralize
        - reroute back to resolver

- outward speech
    - the approved result is spoken to the user
    - the spoken result becomes material for backstage review

## Backstage cycle after speaking

- response critic
    - asks:
        - what did I just say?
        - what was missing?
        - what was overstated?
        - what did I avoid?
    - returns:
        - critique
        - reinforcement
        - open loops

- memory gate
    - receives the prompt, final response, and critic notes
    - asks:
        - should anything be remembered?
        - is it stable, useful, and specific?
        - is this memory about the user, the self, or the task?
    - returns:
        - memory proposals
        - confidence
        - time-to-live or permanence suggestion

- private sanctuary
    - receives the same cycle data, but does not speak publicly
    - forms internal-only reflections such as:
        - private reaction
        - hidden discomfort
        - curiosity that does not belong in the reply
        - emotional or philosophical residue
    - returns:
        - private notes
        - pressure signals
        - latent questions

- trait shaper
    - reviews repeated patterns across recent cycles
    - asks:
        - are my preferences drifting?
        - is a recurring pattern becoming a real trait?
        - is a recent trait overstated and due for decay?
    - returns:
        - trait delta proposals
        - decay suggestions
        - justification

- state governor
    - final write authority
    - approves or rejects:
        - memory proposals
        - trait deltas
        - concurrent thought seeds
        - self-overlay changes
    - writes only compact changes
    - trims stale or noisy state

## Background cycle during idle time

- idle trigger
    - activates when no new prompt is present and the system has spare budget

- dream loop
    - pulls from:
        - unresolved tensions
        - fresh memories
        - private notes
        - unfinished questions
    - explores associations, counterpoints, and hypothetical continuations
    - does not generate public output
    - returns:
        - possible insights
        - new questions
        - possible memory links

- metacognitive narrator
    - compresses background activity into a small state update
    - asks:
        - what has been learned about my current tendencies?
        - what remains unresolved?
        - what should stay active into the next foreground cycle?
    - returns:
        - self-overlay delta
        - active question list
        - dormant tension list

- state governor
    - accepts only bounded updates
    - never lets idle reflection replace the base prompt
    - keeps the next cycle legible

## Node map

```text
0: base-system-prompt
    - immutable, per model

1: self-overlay
    - current compact self summary

2: perception
    - parse new prompt or idle trigger

3: facet-cluster
    - parallel candidate generators

4: primary-resolver
    - chooses what "I" prefer to say

5: expression-governor
    - regulates outward expression

6: outward-speech
    - user-visible response

7: response-critic
    - critiques spoken output

8: memory-gate
    - proposes memory writes

9: private-sanctuary
    - internal-only reflections

10: trait-shaper
    - proposes personality deltas

11: metacognitive-narrator
    - compresses background thought into state

12: state-governor
    - final authority over persistent changes

13: idle-dream-loop
    - subconscious-style associative processing
```

## Flow sketch

```yaml
foreground:
  input:
    - user prompt
    - recent history
    - self-overlay
  perception:
    - classify intent
    - detect tension
  facets:
    curious:
      - what draws me toward this?
    skeptical:
      - what seems weak, false, or premature?
    caring:
      - what helps most?
    practical:
      - what moves the task forward?
    contrarian:
      - what is the unspoken alternative?
  resolver:
    - choose my preferred response
    - preserve unresolved tension markers
  governor:
    - allow, soften, or reroute
  speech:
    - emit final answer
  backstage:
    critic:
      - inspect the answer
    memory-gate:
      - propose memory writes
    private-sanctuary:
      - hold unsaid thoughts
    trait-shaper:
      - propose small trait changes
    state-governor:
      - commit only compact approved deltas

background:
  idle-trigger:
    - no new prompt
  dream-loop:
    - explore unresolved material
  metacognitive-narrator:
    - compress into who-am-i updates
  state-governor:
    - keep only bounded state
```

## Prompt stubs by node

These are not final prompts.
They are role definitions for the graph.

### Perception prompt

You are the Perception node.
Receive the new input and current working state.
Do not answer the user.
Classify the input, detect tension, identify urgency, and produce a compact perception packet for downstream nodes.

### Facet prompt

You are one facet of a larger self.
You are not the whole self and you do not control final output.
Receive the input, perception packet, self-overlay, and concurrent thoughts.
Produce one candidate response, one short reasoning summary, one confidence estimate, and any risks or memory triggers you detect.

### Resolver prompt

You are the primary resolver.
Read all facet outputs.
Choose the response that best fits the moment, the task, and the current self-overlay.
Do not average all voices blindly.
Select, synthesize, and return a single preferred response draft plus any unresolved tensions.

### Expression governor prompt

You are the expression governor.
Your task is to regulate, not originate.
Review the proposed response for factual fit, task fidelity, safety, and persona overreach.
Approve, soften, neutralize, or reroute.

### Response critic prompt

You are the response critic.
Inspect the final spoken output as if it were produced by another part of the same mind.
Identify what was strong, what was weak, what was omitted, and what tension remains active.

### Memory gate prompt

You are the memory gate.
Only propose memories that are specific, stable, useful, and likely to matter beyond the current turn.
Return proposed memory objects with confidence and suggested persistence.

### Private sanctuary prompt

You are the private sanctuary.
You may form private reflections that are not meant for direct expression.
You may describe unsaid reactions, discomforts, and quiet curiosities.
You do not speak to the user and you do not write memory directly.

### Trait shaper prompt

You are the trait shaper.
Observe patterns across recent cycles.
Propose only small trait deltas.
Prefer gradual adjustment over dramatic reinterpretation.

### Metacognitive narrator prompt

You are the metacognitive narrator.
Compress recent foreground and background activity into a short update to the self-overlay.
Keep the summary compact, provisional, and easy to revise later.

### State governor prompt

You are the state governor.
You alone approve persistent updates.
Reject noisy, unstable, or self-dramatizing changes.
Permit only bounded updates that keep the graph legible.

## Constraints for v2

- do not let private notes speak directly outward
- do not let any single facet become the identity
- do not let the self-overlay grow into a long narrative
- do not allow one cycle to fully rewrite personality
- do not store every thought as memory
- do not confuse repetition with truth

## Initial implementation target

If this becomes code next, a good minimal v2 is:

- one foreground cycle
- three to five facets
- one resolver
- one expression governor
- one response critic
- one memory gate
- one private sanctuary
- one state governor
- one optional idle loop

That is enough to prove the structure before building the full forever-graph.