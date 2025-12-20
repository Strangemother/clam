import unittest
from clam import tooler_bot


class TestCreateToolDefinition(unittest.TestCase):
    
    def test_kitchen_heater_definition(self):
        result = tooler_bot.create_tool_definition(tooler_bot.kitchen_heater)
        expected = {
            'type': 'function',
            'function': {
                'name': 'kitchen_heater',
                'description': 'Turn the kitchen header on/off',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'state': {
                            'type': 'boolean',
                            'description': 'Switch state of the heater. True == on'
                        }
                    },
                    'required': ['state']
                }
            }
        }
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
