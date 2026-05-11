"""
run.py — dev server for the spaceship power graph.

Usage:
    python run.py                  # default: ws://localhost:8765, 20 fps
    python run.py --port 9000
    python run.py --fps 60
    python run.py --layout path/to/other.json

Quick Start:

    python run.py --layout ../func-pipes/layouts/spaceship.json
    
"""
import argparse
import asyncio
import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / 'src'))

from power_graph import GraphRunner
from power_graph.ws_server import GraphWSServer

DEFAULT_LAYOUT = (
    pathlib.Path(__file__).parent.parent / 'func-pipes' / 'layouts' / 'spaceship.json'
)

parser = argparse.ArgumentParser(description='Power Graph dev server')
parser.add_argument('--layout', default=str(DEFAULT_LAYOUT), help='Path to layout JSON')
parser.add_argument('--host',   default='localhost')
parser.add_argument('--port',   default=8765, type=int)
parser.add_argument('--fps',    default=20,   type=int)
parser.add_argument('--push',   default=4,    type=int, help='Push state every N ticks')
parser.add_argument('--verbose', action='store_true')
args = parser.parse_args()

logging.basicConfig(
    level=logging.DEBUG if args.verbose else logging.INFO,
    format='%(asctime)s  %(levelname)-7s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

async def main():
    layout = pathlib.Path(args.layout)
    if not layout.exists():
        log.error("Layout not found: %s", layout)
        sys.exit(1)

    log.info("Layout:  %s", layout)
    log.info("Server:  ws://%s:%d   (%d fps, push every %d ticks)",
             args.host, args.port, args.fps, args.push)
    log.info("Client:  open  power_graph/docs/client.html  in your browser")

    runner = GraphRunner(layout, fps=args.fps)
    server = GraphWSServer(runner, host=args.host, port=args.port,
                           push_interval=args.push)
    try:
        await asyncio.gather(runner.run(), server.serve())
    except KeyboardInterrupt:
        pass
    finally:
        await runner.stop()
        log.info("stopped")

asyncio.run(main())
