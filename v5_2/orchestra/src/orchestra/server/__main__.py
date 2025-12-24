"""Run orchestra.server as a module: python -m orchestra.server"""
import argparse
from orchestra.server import main

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Orchestra backbone server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5009, help='Port to listen on')
    args = parser.parse_args()

    print(f"[orchestra.server] Starting on {args.host}:{args.port}")
    main(host=args.host, port=args.port)
