from pathlib import Path

import requests


def file_text(path):
    return Path(path).read_text()


def url_text(url):
    resp = requests.get(url)
    if not resp.ok:
        raise Exception(f"{resp} {resp.reason}")
    return resp.text