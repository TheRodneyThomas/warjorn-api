import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt

from config import SECRET_KEY
from game.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws")
async def game_socket(websocket: WebSocket):
    await websocket.accept()

    # First message must be the JWT token
    try:
        token = await websocket.receive_text()
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload["sub"]
    except (jwt.InvalidTokenError, KeyError):
        await websocket.close(code=1008)  # 1008 = policy violation
        return

    await manager.connect(username, websocket)
    logger.info("Player connected: %s", username)

    try:
        while True:
            data = await websocket.receive_json()
            await handle_action(username, data)
    except WebSocketDisconnect:
        manager.disconnect(username)
        logger.info("Player disconnected: %s", username)


async def handle_action(username: str, data: dict):
    action = data.get("action")

    if action == "ping":
        await manager.send(username, {"event": "pong"})

    else:
        await manager.send(username, {"event": "error", "detail": f"Unknown action: {action}"})
