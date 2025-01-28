import asyncio
# from websockets.asyncio.client import connect
from websockets.sync.client import connect
import json


async def hello():
    url = "ws://192.168.50.60:10000/api/generate/"

    async with connect(url) as websocket:
        jd = {
          "model": "llama3.2",
          "prompt": "Why is the sky blue?"
        }
        await websocket.send(json.dumps(jd))
        message = await websocket.recv()
        print(message)


if __name__ == "__main__":
    asyncio.run(hello())

