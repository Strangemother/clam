"""
Memorybpt - Running on port 9383
"""

import os
import time
import json
import pathlib

from jinja2 import Template
from .client import Client
from clam.backbone import mount

class ToolClient(Client):
    port = 0
    name = None # 'toolclient'
    cache_dir = None # pathlib.Path(f'./cache/{name}/')
    template_path = None # f'templates/{name}.txt'

    def get_template_path(self, name=None):
        n = name or self.get_name()
        return f'templates/{n}.txt'

    def wake(self):
        super().wake()
        mount({
                'name': self.get_name(),
                'id': self.get_name(),
                'host': self.host,
                'port': self.port,
                'type': 'bot',
            })

    def get_cache_dir(self):
        return pathlib.Path(f'./cache/{self.get_name()}/')

    def get_template_dir(self):
        res = pathlib.Path(f'./templates/{self.get_name()}/')

        return res

    def as_cache_path(self, filename):
        """Save to the correct place.
        """
        return self.get_cache_dir() / filename

    def template_rendered(self, sub_template_name=None, *a, **kw):
        """given a sub template name, resolve the template and render
        returning the rendered text.
        """
        template_path = self.get_module_dir() / self.get_template_dir() / sub_template_name
        # with open(template_path, 'r') as f:
        d = {}
        for x in a:
            d.update(x)
        d.update(kw)
        return Template(template_path.read_text()).render(**d)

    def get_module_dir(self):
        return os.path.dirname(__file__)

    def get_template(self, name=None):
        template_path = os.path.join(self.get_module_dir(), self.get_template_path(name))
        with open(template_path, 'r') as f:
            return Template(f.read())

    def get_rendered_template_message(self, message, **info):

        name = info.pop('template_name', None)
        # Render template response
        response = self.get_template(name).render(
            message=message,
            timestamp=time.time(),
            client_name=self.get_name(),
            port=self.port,
            **info
        )

        return response

    def save_json(self, filename, d):
        p = self.as_cache_path(filename)
        os.makedirs(p.parent, exist_ok=True)
        return p.write_text(json.dumps(d, indent=4))


