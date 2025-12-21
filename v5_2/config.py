"""Example config for clam - just set UPPERCASE variables."""

BACKBONE_HOST = '127.0.0.1'
BACKBONE_PORT = 5000
DEBUG = True

# clam cli -f
DEFAULT_PROMPT_FILE = 'prompts/chicken.prompt.md'

# DEFAULT_MODEL = 'tiger-gemma-9b-v3' # Use a specific model by default
DEFAULT_MODEL = "gpt-oss-120b-distill-qwen3-4b-thinking-i1"



GRAPH = {
    'terminal': 'memorybot',
    'memorybot': 'titlebot'
}
