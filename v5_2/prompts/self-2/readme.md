# Self-2 Prompt Pack

This folder contains the first runnable prompt pack for the self-thinking v2 graph.

Primary model:
- granite-4.1-8b

Design goals:
- keep each node narrow and inspectable
- let each node speak in plain text
- separate foreground reply generation from background reflection
- keep private thought and persistent state behind governance gates
- allow a forever loop without a tight runaway cycle during development

## Files

- perception.prompt.md
- facet-curious.prompt.md
- facet-skeptical.prompt.md
- facet-caring.prompt.md
- facet-practical.prompt.md
- facet-contrarian.prompt.md
- primary-resolver.prompt.md
- expression-governor.prompt.md
- response-critic.prompt.md
- memory-gate.prompt.md
- private-sanctuary.prompt.md
- trait-shaper.prompt.md
- idle-dream.prompt.md
- metacognitive-narrator.prompt.md
- state-governor.prompt.md
- self-2.prompting-layout.json

## Runtime notes

- Every prompt is written for granite-4.1-8b and returns plain text, not JSON.
- The graph schema targets the prompting runtime under func-pipes.
- The background loop uses explicit delay nodes between loop hops.
- Delay nodes are set to 3000 ms as a dev-safe default so the loop does not spin continuously.
- The State Governor is the only node allowed to approve persistent updates.

## Flow

```text
foreground input
    perception
    facet packet
        curious
        skeptical
        caring
        practical
        contrarian
    resolver packet
    primary resolver
    expression governor
    outward speech
    backstage packet
        response critic
        memory gate
        private sanctuary
    trait packet
    trait shaper
    state packet
    state governor
        background delay A
        idle dream
        background delay B
        metacognitive narrator
        background delay C
        state packet ...
```

## Intent

This is a bridge build.
It is not the final forever-brain.

The point of this pack is to make the system legible enough to run, inspect, and tune before adding more hidden state, richer memory, or more autonomous background activity.