# Terminal Client

This tool is to guide using the terminal client

     py -m clam.terminal_client userpersona -c info.json

The terminal can communiate directly to the model, given a prompt

```bash
    clam cli -f prompts/example.prompt.md
    # If the path matches this format, you can provide a name
    clam cli example
```

A Prompt file meta data may define some pre-defined content

```
---
model: gpt-oss-120b-distill-qwen3-4b-thinking-i1
title: first person narrative
type: conversation
---

prompt here
```


