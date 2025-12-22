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
SERVICE_COMPLETIONS_PATH = '/v1/chat/completions/'
SERVICE_GENERATE_PATH = '/api/generate/'

DEFAULT_MODEL = None # Use service default model if not specified

GRAPH = {
    # 'eric': ['dave'],
    # 'dave': 'eric',

    'terminal': 'memorybot',
    'memorybot': 'titlebot'
}

SERVICES = {
    "lmstudio": {
        "host": 'http://192.168.50.60:1234',
        "type": "network",
        'service_completions_path': '/v1/chat/completions/',
        'service_generate_path': '/api/generate/',

    },

    "digital_ocean.oss": {
        "host": "https://krzw4vkfn6kemdbxvuozumkc.agents.do-ai.run",
        "type": "cloud",
        'service_completions_path': '/api/v1/chat/completions',
        # 'service_generate_path': '/api/generate/',
        "headers": {
            "Authorization": f"Bearer 1AfU63trYozPKE0mVH_5fuKH5pXow6dW"
        }
    },
    "digital_ocean.llama": {
        "host": 'https://esin7c5xg2zbu5e3oapo2w3f.agents.do-ai.run',
        "type": "cloud",
        'service_completions_path': '/api/v1/chat/completions',
        # 'service_generate_path': '/api/generate/',
        "headers": {
            "Authorization": f"Bearer TfbFFXnW-yZk0HkTYCwo4l7uQXCvzl5x"
        }
    },

    "voice": {
        'host': "ws://192.168.50.60:42003"
    }
}