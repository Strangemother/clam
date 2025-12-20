

import inspect
import re


def kitchen_heater(state: bool):
    """Turn the kitchen header on/off
    
    arguments:
        state: Switch state of the heater. True == on

    """
    print('Run code.')

def kitchen_header_status():
    """Get the current status of the kitchen heater

    arguments:
        None
    """
    return {'state': True}

def definition_to_partials(definition):
    """Given a tool definition from a message repsonse,
    convert to a dict of partial definitions for execution:

        tool_calls = [{
            'type': 'function',
            "id": "50395859",
            "function": {
                "name": "kitchen_heater",
                "arguments": "{ \"state\": true }"
        }]

    call:
    
        definition_to_partials(tool_calls)

    result:

        {
            "50395859": partial("loc.kitchen_heater", state=True)
        }
    """
    # load tools dict.
    partials = {

    }
    # use pydoc.locate to get function from string


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


TOOLS = [
    kitchen_heater,
    kitchen_header_status
]

tools_map = {x.__name__: x for x in TOOLS}

tool_calls = [create_tool_definition(tools_map[v]) for k,v in tools_map.items()]