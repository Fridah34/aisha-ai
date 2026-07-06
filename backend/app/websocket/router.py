from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import json
import asyncio
from typing import Dict, Set

router = APIRouter(tags=["WebSocket"])

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        # Accept the connection with proper headers
        await websocket.accept(
            subprotocols=websocket.request.headers.get("sec-websocket-protocol", "").split(", ") if websocket.request.headers.get("sec-websocket-protocol") else []
        )
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        print(f"✅ User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
        return True
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"❌ User {user_id} disconnected")
    
    async def broadcast_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            message_json = json.dumps(message)
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    print(f"Failed to send message: {e}")
                    dead_connections.append(connection)
            
            for conn in dead_connections:
                self.disconnect(conn, user_id)

manager = ConnectionManager()

@router.websocket("/ws/conversations/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    print(f"🔌 WebSocket connection attempt from user {user_id}")
    
    try:
        # Accept the connection immediately
        await websocket.accept()
        print(f"✅ WebSocket accepted for user {user_id}")
        
        # Register connection
        if user_id not in manager.active_connections:
            manager.active_connections[user_id] = set()
        manager.active_connections[user_id].add(websocket)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "user_id": user_id,
            "message": "Connected to AISHA real-time updates"
        }))
        print(f"📨 Sent connection confirmation to user {user_id}")
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    print(f"📨 Received from client {user_id}: {message}")
                    
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                        print(f"🏓 Sent pong to user {user_id}")
                    elif message.get("type") == "test":
                        await websocket.send_text(json.dumps({
                            "type": "test_response",
                            "message": f"Echo: {message.get('message')}"
                        }))
                except json.JSONDecodeError:
                    if data == "ping":
                        await websocket.send_text("pong")
                        print(f"🏓 Sent pong to user {user_id}")
                        
            except WebSocketDisconnect:
                print(f"⚠️ WebSocket disconnect detected for user {user_id}")
                break
            except Exception as e:
                print(f"❌ Error in WebSocket loop for user {user_id}: {e}")
                break
                
    except WebSocketDisconnect:
        if user_id in manager.active_connections:
            manager.active_connections[user_id].discard(websocket)
        print(f"❌ User {user_id} disconnected")
    except Exception as e:
        print(f"❌ WebSocket error for user {user_id}: {e}")
        try:
            if user_id in manager.active_connections:
                manager.active_connections[user_id].discard(websocket)
        except:
            pass

async def broadcast_status_change(user_id: int, customer_id: int, new_status: str):
    await manager.broadcast_to_user(user_id, {
        "type": "status_change",
        "customer_id": customer_id,
        "new_status": new_status,
        "timestamp": asyncio.get_event_loop().time()
    })