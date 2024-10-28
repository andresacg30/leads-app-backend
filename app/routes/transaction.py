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
        logger.info("Authentication failed; closing connection")
        return
    await websocket.accept()
    user_id = str(user.id)
    user_connections[user_id].append(websocket)
    logger.info(f"User {user_id} connected via WebSocket")
    try:
        while True:
            await asyncio.sleep(1)  # Keep the connection alive
    except WebSocketDisconnect:
        logger.info(f"WebSocketDisconnect for user {user_id}")
    except Exception as e:
        logger.error(f"Exception in WebSocket for user {user_id}: {e}")
    finally:
        if websocket in user_connections[user_id]:
            user_connections[user_id].remove(websocket)
            logger.info(f"Removed websocket for user {user_id}")
