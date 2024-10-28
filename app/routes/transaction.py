import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from app.controllers.user import user_connections
from app.models.user import UserModel
from app.auth.jwt_bearer import get_current_user


router = APIRouter(prefix="/api/transaction", tags=["transaction"])


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_current_user_from_websocket(websocket: WebSocket) -> UserModel:
    token = websocket.query_params.get("token")
    if not token:
        logger.info("Token missing")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    logger.info(f"Token received: {token}")
    user = await get_current_user(authorization=token)
    if not user:
        logger.info("Invalid token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return user


@router.websocket("/ws/get-current-credit")
async def get_current_credit(websocket: WebSocket):
    user = await get_current_user_from_websocket(websocket)
    if not user:
        return
    await websocket.accept()
    user_connections[user.id].append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        user_connections[user.id].remove(websocket)
        print(f"Client disconnected: {user.id}")
