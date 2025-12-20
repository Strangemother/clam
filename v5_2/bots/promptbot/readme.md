# Prompt Bot

The prompt bot accepts a standard prompt file to use as the respond instruction.

    run -m bots.promptbot --prompt-file prompts/chicken.prompt.md
    # Server running on http://127.0.0.1:9394

The prompt is given as a `system` role message. The subsequent user message from the interface is applied as the `user` role

This _single message_ per query does not continue the conversation, unlike the terminal cli of which can select and converse with a prompt file