from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.helpers import conversations, messages, users as users_helper
from app.utilities.logger import logger
from app.helpers.twilio import send_message as send_msg_twilio
from app.models.user import UserRoleEnum
from app.models.message import Message, SenderTypeEnum
from app.models.conversation import ConversationStateEnum
from app.models.websockets import (
    ChatWebSocketResponseType,
    ChatWebSocketResponse,
    StatusData, Notification,
    NotificationType, MessageData,
    SenderType
)
from app.utilities.socket import socket_manager, WebSocketConfig, WebSocketType
from datetime import datetime
from app.config import settings


import httpx

router = APIRouter()


@router.post("/send")
async def send_message(conversation_id: int, message: MessageData):
    """
    Send a message to a conversation.

    Args:
    conversation_id (int): The ID of the conversation.
    message (MessageData): The message to be sent.

    Returns:
    None
    """
    await socket_manager.send_message(conversation_id, message)


async def rollback_message(message: Message, websocket: WebSocket):
    """
    Rollback a message by deleting it from the database and sending an error response.

    Args:
    message (Message): The message to be rolled back.
    websocket (WebSocket): The WebSocket connection.

    Returns:
    None
    """
    # Delete message from database
    messages.delete_message(message.id)
    # Send error response
    await websocket.send_json(ChatWebSocketResponse(
        type=ChatWebSocketResponseType.STATUS,
        status=StatusData(success=False, message="Error sending message to client through Twilio")
    ).model_dump(exclude_none=True))


@router.websocket("/{conversation_id}/ws")
async def websocket_endpoint(websocket: WebSocket, conversation_id: int, user_id: str):
    """
    Establish a WebSocket connection for a conversation.

    Args:
    websocket (WebSocket): The WebSocket connection.
    conversation_id (int): The ID of the conversation.
    user_id (str): The ID of the user.

    Returns:
    None
    """
    await websocket.accept()
    # TODO: Validate access token
    # Get conversation by id
    conversation = conversations.get_conversation_by_id(conversation_id)
    if not conversation:
        await websocket.send_json(ChatWebSocketResponse(
            type=ChatWebSocketResponseType.STATUS,
            status=StatusData(success=False, message="Conversation not found")
        ).model_dump(exclude_none=True))
        await websocket.close()
        return
    user = users_helper.get_user_by_id(user_id)
    if not user:
        await websocket.send_json(ChatWebSocketResponse(
            type=ChatWebSocketResponseType.STATUS,
            status=StatusData(success=False, message="User not found")
        ).model_dump(exclude_none=True))
        await websocket.close()
        return
    # Check if user is assigned to the conversation as an agent
    if conversation.assigned_user_id != user.id and user.role_id == UserRoleEnum.AGENT.value:
        await websocket.send_json(ChatWebSocketResponse(
            type=ChatWebSocketResponseType.STATUS,
            status=StatusData(success=False, message="User is not assigned to this conversation")
        ).model_dump(exclude_none=True))
        await websocket.close()
        return
    # Check if conversation is closed
    if conversation.state_id == ConversationStateEnum.CLOSED.value:
        await websocket.send_json(ChatWebSocketResponse(
            type=ChatWebSocketResponseType.STATUS,
            status=StatusData(success=False, message="Conversation is closed")
        ).model_dump(exclude_none=True))
        await websocket.close()
        return
    # Add connection to socket manager
    await socket_manager.add_connection(WebSocketConfig(
        ws_type=WebSocketType.CONVERSATION,
        user_id=user_id, conversation_id=conversation_id
    ), websocket)
    try:
        while True:
            agent_message = await websocket.receive_text()
            logger.info(f"Message from {user_id} in conversation {conversation_id}: {agent_message}")
            message = Message(
                conversation_id=conversation_id,
                content=agent_message,
                sender_type=SenderTypeEnum.AGENT,
                user_id=user_id
            )
            # Save message in database
            message, message_media = messages.save_message(message, conversation_id)
            if not message:
                logger.error("Error saving message: " + message)
                await websocket.send_json(ChatWebSocketResponse(
                    type=ChatWebSocketResponseType.STATUS,
                    status=StatusData(success=False, message="Error saving message")
                ).model_dump(exclude_none=True))
                continue
            # Send message to client
            if not settings.testing:
                try:
                    twilio_response = await send_msg_twilio(conversation.client_phone, agent_message)
                except httpx.HTTPError as e:
                    logger.error(f"Error sending message to client: {e}")
                    # Rollback message
                    await rollback_message(message, websocket)
                    continue
                if not twilio_response.status_code == httpx.codes.OK:
                    logger.error("Error sending message to client")
                    # Rollback message
                    await rollback_message(message, websocket)
                    continue
            # Send message to users up in the hierarchy based on assigned user
            users_to_notify = users_helper.get_user_ancestors(conversation.assigned_user_id)
            if users_to_notify:
                # If connected user is not the assigned user, send notification to assigned user
                if conversation.assigned_user_id:
                    users_to_notify.append(conversation.assigned_user_id)
                for ancestor_id in users_to_notify:
                    await socket_manager.send_notification(ancestor_id, Notification(
                        type=NotificationType.NEW_MESSAGE,
                        message=MessageData(
                            content=agent_message,
                            timestamp=datetime.now(),
                            conversation_id=conversation_id,
                            created_at=message.created_at,
                            user_id=user.id,
                            user_name=user.full_name,
                            sender_type=SenderType.AGENT
                        )
                    ))
            # Send success response
            await websocket.send_json(ChatWebSocketResponse(
                type=ChatWebSocketResponseType.STATUS,
                status=StatusData(success=True, message="Message sent")
            ).model_dump(exclude_none=True))
    except WebSocketDisconnect:
        await socket_manager.remove_connection(WebSocketConfig(
            ws_type=WebSocketType.CONVERSATION,
            conversation_id=conversation_id,
            user_id=user_id
        ))
        logger.info(f"Conversation {conversation_id} disconnected")
    except Exception as e:
        logger.error(f"Error in websocket: {e}")