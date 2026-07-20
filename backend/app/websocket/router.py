import asyncio
import json
import uuid
from typing import Dict, Set

from app.auth.utils import verify_access_token
from app.database import get_db
from app.models import User
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

router = APIRouter(tags=["WebSocket"])


# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[uuid.UUID, Set[WebSocket]] = {}

    def disconnect(self, websocket: WebSocket, business_id: uuid.UUID):
        if business_id in self.active_connections:
            self.active_connections[business_id].discard(websocket)
            if not self.active_connections[business_id]:
                del self.active_connections[business_id]
        print(f"Business {business_id} disconnected")

    async def broadcast_to_business(self, business_id: uuid.UUID, message: dict):
        if business_id in self.active_connections:
            message_json = json.dumps(message)
            dead_connections = []
            for connection in self.active_connections[business_id]:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    print(f"Failed to send message: {e}")
                    dead_connections.append(connection)

            for conn in dead_connections:
                self.disconnect(conn, business_id)


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


@router.websocket("/ws/{business_id}")
@router.websocket("/ws/conversations/{business_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    user = _authenticate_websocket(websocket, db)
    if not user:
        await websocket.close(code=4401, reason="Not authenticated")
        return

    if user.id != business_id:
        await websocket.close(code=4403, reason="Business mismatch")
        return

    print(f"Websocket connection attempt for business {business_id}")

    try:
        await websocket.accept()
        print(f"WebSocket accepted for business {business_id}")

        if business_id not in manager.active_connections:
            manager.active_connections[business_id] = set()
        manager.active_connections[business_id].add(websocket)

        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_established",
                    "business_id": str(business_id),
                    "message": "Connected to AISHA real-time updates",
                }
            )
        )
        print(f"Sent connection confirmation for business {business_id}")

        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    print(f"Received from business client {business_id}: {message}")

                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                        print(f"Sent pong to business {business_id}")
                    elif message.get("type") == "test":
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "test_response",
                                    "message": f"Echo: {message.get('message')}",
                                }
                            )
                        )
                except json.JSONDecodeError:
                    if data == "ping":
                        await websocket.send_text("pong")
                        print(f"Sent pong to business {business_id}")

            except WebSocketDisconnect:
                print(f"WebSocket disconnect detected for business {business_id}")
                break
            except Exception as e:
                print(f"Error in WebSocket loop for business {business_id}: {e}")
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket, business_id)
        print(f"Business {business_id} disconnected")
    except Exception as e:
        print(f"WebSocket error for business {business_id}: {e}")
        manager.disconnect(websocket, business_id)


async def broadcast_status_change(
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    new_status: str,
):
    await manager.broadcast_to_business(
        business_id,
        {
            "type": "status_change",
            "customer_id": str(customer_id),
            "new_status": new_status,
            "timestamp": asyncio.get_event_loop().time(),
        },
    )
