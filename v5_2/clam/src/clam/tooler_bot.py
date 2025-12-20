

import inspect
import re


def kitchen_heater(state: bool):
    """Turn the kitchen header on/off
    
    arguments:
        state: Switch state of the heater. True == on

    """
    print('Run code.')


def create_tool_definition(func):
    """Given a function, return a dictionary explaining the utility for
    tool calling.

        create_tool_definition(kitchen_heater)

    result:

        {
            'type': 'function',
            "function": {
                "name": "kitchen_heater",
                "description": "Turn the kitchen header on/off",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "bool",
                            "description": "Switch state of the heater. True == on",
                        }
                    },
                    "required": ["state"]
                }
            }
        }
    """
    type_map = {
        'bool': 'boolean',
        'str': 'string',
        'int': 'integer',
        'float': 'number',
        'list': 'array',
        'dict': 'object'
    }
    
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    
    parts = doc.split('arguments:', 1)
    description = parts[0].strip()
    
    arg_descriptions = {}
    if len(parts) > 1:
        for match in re.finditer(r'^\s*(\w+):\s*(.+?)(?=^\s*\w+:|$)',
                                parts[1], re.MULTILINE | re.DOTALL):
            arg_descriptions[match.group(1)] = match.group(2).strip()
    
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue
        
        if param.annotation != inspect.Parameter.empty:
            type_name = getattr(param.annotation, '__name__', str(param.annotation))
            param_type = type_map.get(type_name, 'string')
        else:
            param_type = 'string'
        
        properties[param_name] = {
            'type': param_type,
            'description': arg_descriptions.get(param_name, '')
        }
        
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    return {
        'type': 'function',
        'function': {
            'name': func.__name__,
            'description': description,
            'parameters': {
                'type': 'object',
                'properties': properties,
                'required': required
            }
        }
    }
