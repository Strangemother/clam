"""Serve the socket spy from its own directory.

Run from anywhere::

    python examples/spy/run.py

Then open http://127.0.0.1:8000/.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Read the host and port used by the development HTTP server."""
    parser = argparse.ArgumentParser(description="Serve the Func Sockets spy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    return parser.parse_args()


def main() -> None:
    """Serve the files beside this script until interrupted."""
    args = parse_args()
    directory = Path(__file__).resolve().parent
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Socket spy: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
