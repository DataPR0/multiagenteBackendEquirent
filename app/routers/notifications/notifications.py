from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.helpers.users import change_user_state
from app.models.user import UserStateEnum
from app.utilities.socket import socket_manager, WebSocketConfig, WebSocketType
from app.utilities.logger import logger
from app.models.websockets import Notification

router = APIRouter()


@router.post("/send")
async def send_notification(user_id: str, notification: Notification):
    """
    Send a notification to a user.

    Args:
    - user_id (str): The ID of the user to send the notification to.
    - notification (Notification): The notification to send.

    Returns:
    - A dictionary with a message indicating the notification was sent.
    """
    await socket_manager.send_notification(user_id, notification)
    return {"message": "Notification sent"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    Establish a WebSocket connection for receiving notifications.

    Args:
    - websocket (WebSocket): The WebSocket object.
    - user_id (int): The ID of the user establishing the connection.

    Returns:
    - None
    """
    await websocket.accept()
    await socket_manager.add_connection(WebSocketConfig(
        ws_type=WebSocketType.NOTIFICATIONS,
        user_id=user_id
    ), websocket)
    user = change_user_state(user_id, UserStateEnum.ONLINE.value)
    if not user:
        logger.error(f"Error changing user {user_id} state to ONLINE")
    logger.info(f"User {user_id} connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await socket_manager.remove_connection(WebSocketConfig(
            ws_type=WebSocketType.NOTIFICATIONS,
            user_id=user_id
        ))
        user = change_user_state(user_id, UserStateEnum.OFFLINE.value)
        if not user:
            logger.error(f"Error changing user {user_id} state to OFFLINE")
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"Error in websocket: {e}")