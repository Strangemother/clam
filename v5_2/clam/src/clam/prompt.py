import pathlib
import markdown
# from markdown import markdown
from jinja2 import Template


HERE =  pathlib.Path(__file__).parent


class Prompt:
    """Is a file with extras.
    """
    def __init__(self, path, context=None):
        self.path = pathlib.Path(path)
        self.context = context or {}
        self._processed = False
        if path:
            self.process_prompt()

    def process_prompt(self):
        """Read markdown, process content and meta
        """
        md = markdown.Markdown(extensions=['meta'])
        self.raw_text = self.path.read_text()
        self.html = md.convert(self.raw_text)
        self.raw_meta = md.Meta
        self.content = '\n'.join(md.lines)
        self._processed = True

    def get_models(self):
        v = self.raw_meta.get('models', []) or []
        v += self.raw_meta.get('model', []) or []
        if len(v) == 0:
            v.append('auto')
        return v

    def render(self, **kw):
        kw.update(self.context)
        return Template(self.content).render(**kw)


    @property
    def title(self):
        return self.get_meta_key('title')

    @property
    def type(self):
        return self.get_meta_key('type', 'conversation')

    def get_meta_key(self, key, default=None):
        v = self.raw_meta.get(key, []) or []
        if len(v) == 0:
            return default
        return v[0]

    @property
    def model(self):
        res = self.get_models()[0]
        if res == 'auto':
            # return config model
            # return "granite-4.0-h-350m-unsloth-hybrid"
            return "granite-4.0-h-tiny"

        return res

    def __str__(self):
        v = str(self.path.relative_to(self.path.parent))
        return f'<{self.__class__.__name__}("{v}")>'