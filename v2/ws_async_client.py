import asyncio
from websockets.asyncio.client import connect


async def hello():
    url = "ws://192.168.50.60:10000"

    async with connect(url) as websocket:
        await websocket.send("Hello world!")
        message = await websocket.recv()
        print(message)


if __name__ == "__main__":
    asyncio.run(hello())