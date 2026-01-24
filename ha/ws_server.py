"""Minimal WebSocket server to broadcast HA events to browser clients."""
import asyncio
import websockets
import json

CLIENTS = set()

async def handler(websocket):
    CLIENTS.add(websocket)
    try:
        async for _ in websocket:
            pass  # We only broadcast, don't receive
    finally:
        CLIENTS.discard(websocket)

async def broadcast(data):
    if CLIENTS:
        msg = json.dumps(data)
        await asyncio.gather(*[c.send(msg) for c in CLIENTS])

async def start_server(host="0.0.0.0", port=8765):
    async with websockets.serve(handler, host, port):
        print(f"WebSocket server running on ws://{host}:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(start_server())
