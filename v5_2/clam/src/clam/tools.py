"""clam.tools provides assets and functionality for loading and associating
python functions with tools request.
"""
from pydoc import locate

def resolve_modules(modules):
    # All modules are loaded, functions are returned flat

    locs = {}
    for m in (modules or []):
        locs[m] = locate(m)

    # Now flatten
    return flatten_modules_dict(locs)


def flatten_modules_dict(modules_dict):
    """Given a dict, return functions
    """
    r = ()
    for k, v in modules_dict.items():
        names = dir(v)
        for n in names:
            if n.startswith('_'):
                continue
            unit = getattr(v, n)
            if callable(unit):
                r += (unit,)
    return r