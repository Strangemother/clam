"""
Memorybpt - Running on port 9383
"""

import os
import time
import json
import pathlib

from jinja2 import Template
from client import Client

class ToolClient(Client):
    port = 0
    name = 'toolclient'
    cache_dir = None # pathlib.Path(f'./cache/{name}/')
    template_path = None # f'templates/{name}.txt'

    def get_template_path(self):
        return f'templates/{self.name}.txt'

    def get_cache_dir(self):
        return pathlib.Path(f'./cache/{self.name}/')

    def as_cache_path(self, filename):
        """Save to the correct place.
        """
        return self.get_cache_dir() / filename


    def get_template(self):
        template_path = os.path.join(os.path.dirname(__file__), self.get_template_path())
        with open(template_path, 'r') as f:
            return Template(f.read())


    def get_rendered_template_message(self, message, **info):

        # Render template response
        response = self.get_template().render(
            message=message,
            timestamp=time.time(),
            client_name=self.name,
            port=self.port,
            **info
        )

        return response

    def save_json(self, filename, d):
        p = self.as_cache_path(filename)
        os.makedirs(p.parent, exist_ok=True)
        return p.write_text(json.dumps(d, indent=4))


