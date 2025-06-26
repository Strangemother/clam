
from pathlib import Path


def file_text(path):
    return Path(path).read_text()