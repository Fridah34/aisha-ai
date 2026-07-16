from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from sqlalchemy.orm import Session
import json
import asyncio
from typing import Dict, Set

from app.database import get_db
from app.models import User
from app.auth.utils import verify_access_token

router = APIRouter(tags=["WebSocket"])

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"User {user_id} disconnected")

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


def _authenticate_websocket(websocket: WebSocket, db: Session) -> User | None:
    """
    Reads the access token cookie directly off the WebSocket handshake request.
    Same cookie, same verify_access_token(), mirroring the HTTP auth dependency
    manually since Depends(get_current_user) doesn't apply cleanly to websockets.
    """
    token = websocket.cookies.get("access_token")
    if not token:
        return None

    token_data = verify_access_token(token)
    if not token_data:
        return None

    email = token_data.get("email") or token_data.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None

    return user


@router.websocket("/ws/conversations/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    db: Session = Depends(get_db),
):
    user = _authenticate_websocket(websocket, db)
    if not user:
        await websocket.close(code=4401, reason="Not authenticated")
        return

    if user.id != user_id:
        await websocket.close(code=4403, reason="User mismatch")
        return

    print(f"Websocket connection attempt from user {user_id}")

    try:
        await websocket.accept()
        print(f"WebSocket accepted for user {user_id}")

        if user_id not in manager.active_connections:
            manager.active_connections[user_id] = set()
        manager.active_connections[user_id].add(websocket)

        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "user_id": user_id,
            "message": "Connected to AISHA real-time updates"
        }))
        print(f"Sent connection confirmation to user {user_id}")

        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    print(f"Received from client {user_id}: {message}")

                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                        print(f"Sent pong to user {user_id}")
                    elif message.get("type") == "test":
                        await websocket.send_text(json.dumps({
                            "type": "test_response",
                            "message": f"Echo: {message.get('message')}"
                        }))
                except json.JSONDecodeError:
                    if data == "ping":
                        await websocket.send_text("pong")
                        print(f"Sent pong to user {user_id}")

            except WebSocketDisconnect:
                print(f"WebSocket disconnect detected for user {user_id}")
                break
            except Exception as e:
                print(f"Error in WebSocket loop for user {user_id}: {e}")
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        print(f"User {user_id} disconnected")
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)


async def broadcast_status_change(user_id: int, customer_id: int, new_status: str):
    await manager.broadcast_to_user(user_id, {
        "type": "status_change",
        "customer_id": customer_id,
        "new_status": new_status,
        "timestamp": asyncio.get_event_loop().time()
    })