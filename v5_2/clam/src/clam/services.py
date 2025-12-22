"""Service endpoint management for clam."""
from . import config

#$AGENT_ENDPOINT/api/v1/chat/completions
do_instance = "https://krzw4vkfn6kemdbxvuozumkc.agents.do-ai.run"
#  -H "Authorization: Bearer $AGENT_ACCESS_KEY"
do_key = 'n0CW2L-SNcS0VHzzC0oanqdRtqYojsGX'

do_instance = "https://esin7c5xg2zbu5e3oapo2w3f.agents.do-ai.run"
do_key = "A5e3_jlOcpzAbDBTgVgMeYiWQx1xw2La"
# {
#     "messages": [
#       {
#         "role": "user",
#         "content": "What is the capital of France?"
#       }
#     ],

#     "stream": False,
#     "include_functions_info": False,
#     "include_retrieval_info": False,
#     "include_guardrails_info": False
#   }



def get_service_endpoint(endpoint_type='completions', name='lmstudio'):
    """Build the service endpoint URL.

    Args:
        endpoint_type: Type of endpoint ('completions' or 'generate')

    Returns:
        Full URL to the service endpoint
    """
    unit = config.SERVICES.get(name)
    if unit is None:
        print('Issue: no service in config named:', name)
        unit = {}

    urlmap = {
        'completions': unit.get('service_completions_path', config.SERVICE_COMPLETIONS_PATH),
        'generate': unit.get('service_generate_path', config.SERVICE_GENERATE_PATH),
    }
    path = urlmap.get(endpoint_type.lower())
    if path is None:
        raise ValueError(f"Unknown endpoint type: {endpoint_type}")

    HOST = unit['host']
    host = f"{HOST}"
    # host = config.SERVICE_HOST
    # Ensure no double slashes
    if host.endswith('/'):
        host = host.rstrip('/')
    if path.startswith('/'):
        path = path.lstrip('/')
    return f"{host}/{path}"


def service_endpoint(endpoint_type='completions'):
    """Alias for get_service_endpoint for backward compatibility."""
    return get_service_endpoint(endpoint_type)
