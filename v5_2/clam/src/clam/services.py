"""Service endpoint management for clam."""
from . import config


def get_service_endpoint(endpoint_type='completions'):
    """Build the service endpoint URL.
    
    Args:
        endpoint_type: Type of endpoint ('completions' or 'generate')
        
    Returns:
        Full URL to the service endpoint
    """    
    urlmap = {
        'completions': config.SERVICE_COMPLETIONS_PATH,
        'generate': config.SERVICE_GENERATE_PATH,
    }
    path = urlmap.get(endpoint_type.lower())
    if path is None:
        raise ValueError(f"Unknown endpoint type: {endpoint_type}")
    
    host = config.SERVICE_HOST
    # Ensure no double slashes
    if host.endswith('/'):
        host = host.rstrip('/')
    if path.startswith('/'):
        path = path.lstrip('/')
    return f"{host}/{path}"


def service_endpoint(endpoint_type='completions'):
    """Alias for get_service_endpoint for backward compatibility."""
    return get_service_endpoint(endpoint_type)
