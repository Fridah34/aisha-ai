import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/conversations/1"
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
            
            print("✅ All tests passed!")
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed: {e}")
    except ConnectionRefusedError:
        print("❌ Connection refused. Is FastAPI running?")
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
