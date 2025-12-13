"""Global configuration for clam."""
import importlib.util
from pathlib import Path

def _load_module(path):
    """Load a Python file as a module and extract UPPERCASE vars."""
    spec = importlib.util.spec_from_file_location("cfg", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    
    result = {}
    for key in dir(mod):
        if key.isupper():
            result[key] = getattr(mod, key)
    return result

# Load defaults first
_defaults_path = Path(__file__).parent / 'defaults.config.py'
_defaults = _load_module(_defaults_path)
globals().update(_defaults)

def load(config_path=None):
    """Load user config from Python file, overriding defaults."""
    if not config_path:
        # Try default names in cwd
        for name in ['clam.config.py', 'clamconfig.py', 'config.py']:
            p = Path.cwd() / name
            if p.exists():
                config_path = p
                break
    
    if not config_path:
        return False
    
    path = Path(config_path)
    if not path.exists():
        return False
    
    # Load user config and override defaults
    user_config = _load_module(path)
    globals().update(user_config)
    
    return True
