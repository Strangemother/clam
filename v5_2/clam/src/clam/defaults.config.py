"""Default configuration values for clam.

This file documents all available settings and their defaults.
User config files will override these values.
"""

# Backbone service host (use '0.0.0.0' for all interfaces, '127.0.0.1' for local only)
BACKBONE_HOST = '0.0.0.0'

# Backbone service port
BACKBONE_PORT = 5000

# Enable debug mode (auto-reload, detailed errors)
DEBUG = False

# Bot service URLs
CLIENT_A_URL = 'http://localhost:8010'
FILENAMER_URL = 'http://localhost:9394'

# Bot ports
MEMORYBOT_PORT = 9383

# Terminal chat settings
DEFAULT_PROMPT_FILE = 'prompts/angry-bot.prompt.md'
PROMPT_DIR = './prompts'

# LLM Service endpoints
SERVICE_HOST = 'http://192.168.50.60:1234'
SERVICE_COMPLETIONS_PATH = '/v1/chat/completions'
SERVICE_GENERATE_PATH = '/api/generate/'

DEFAULT_MODEL = None # Use service default model if not specified

DO_INSTANCE = "https://krzw4vkfn6kemdbxvuozumkc.agents.do-ai.run"
do_key = 'example_VKpEgXygPVXd972FugbqMYoBLNC1AStf'

GRAPH = {
    # 'eric': ['dave'],
    # 'dave': 'eric',

    'terminal': 'memorybot',
    'memorybot': 'titlebot'
}

SERVICES = {
    "lmstudio": {
        "host": SERVICE_HOST,
        "type": "network"
    },

    "digital_ocean.oss": {
        "host": DO_INSTANCE,
        "type": "cloud",
        "headers": {
            "Authorization": f"Bearer {do_key}"
        }
    },    
    "digital_ocean.llama": {
        "host": DO_INSTANCE,
        "type": "cloud", 
        "headers": {
            "Authorization": f"Bearer {do_key}"
        }
    }
}