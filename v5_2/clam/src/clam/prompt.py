import pathlib
import markdown
# from markdown import markdown


HERE =  pathlib.Path(__file__).parent


class Prompt:
    """Is a file with extras.
    """
    def __init__(self, path):
        self.path = pathlib.Path(path)
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

    @property
    def title(self):
        return self.get_meta_key('title')

    def get_meta_key(self, key, default=None):
        v = self.raw_meta.get('title', []) or []
        if len(v) == 0:
            return default
        return v[0]

    @property
    def model(self):
        res = self.get_models()[0]
        if res == 'auto':
            # Grab from config defaults.
            from . import config
            res = config.DEFAULT_MODEL

            # return config model
            # return "granite-4.0-h-350m-unsloth-hybrid"
            # return "granite-4.0-h-tiny"

        return res