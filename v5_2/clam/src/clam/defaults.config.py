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
