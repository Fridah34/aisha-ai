import asyncio

import websockets


async def test():
    async with websockets.connect("ws://localhost:8000/ws/test") as ws:
        print(await ws.recv())  # Should print "Test connection successful!"
        await ws.send("Hello!")
        print(await ws.recv())  # Should print "Echo: Hello!"


asyncio.run(test())
