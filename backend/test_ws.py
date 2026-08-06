import asyncio
import json

import websockets


async def test_websocket():
    uri = "ws://localhost:8000/ws/conversations/1"
    print(f"🔌 Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")

            # Receive connection confirmation
            response = await websocket.recv()
            print(f"📨 Received: {response}")

            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("📤 Sent ping")

            # Receive pong
            response = await websocket.recv()
            print(f"📨 Received: {response}")

            # Send test message
            await websocket.send(
                json.dumps({"type": "test", "message": "Hello WebSocket"})
            )
            print("📤 Sent test message")

            # Receive test response
            response = await websocket.recv()
            print(f"📨 Received: {response}")

            print("✅ All tests passed!")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed: {e}")
    except ConnectionRefusedError:
        print("❌ Connection refused. Is FastAPI running?")
    except Exception as e:  # noqa: BLE001
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e)}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
