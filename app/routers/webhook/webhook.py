import httpx
import asyncio
from fastapi import APIRouter, Request, HTTPException
from app.helpers import messages, conversations, users
from app.helpers.chatbot import load_chatbot_messages
from app.helpers.messages import save_message
from app.helpers.twilio import send_message, end_conversation
from app.models.message import Message, SenderTypeEnum
from app.models.user import UserRoleEnum
from app.models.conversation import ConversationStateEnum
from app.utilities.logger import logger
from app.utilities.socket import socket_manager
from app.models.websockets import Notification, NotificationType, MessageData, SenderType


router = APIRouter()

DEFAULT_MESSAGE = """
Gracias por contactarnos. En este momento, no hemos podido asignar tu conversación a un asesor.

🔄 ¿Qué puedes hacer?

Intentarlo nuevamente más tarde.
Revisar nuestras preguntas frecuentes aquí: https://www.finanzauto.com.co/portal/pqrinter
Si es urgente, contáctanos por otro canal: (601) 749 9000.
Lamentamos las molestias y agradecemos tu paciencia.

📍 Finanzauto S.A. BIC
"""


async def send_default_message(thread_id: str):
    await asyncio.sleep(30 * 60)  # Wait for 5 minutes
    logger.info(f"Sending default message to: {thread_id}")
    conversation = conversations.get_conversation_by_thread_id(thread_id)
    if not conversation.assigned_user_id and conversation.state_id != ConversationStateEnum.CLOSED:
        message_count = conversations.get_conversation_user_messages_count(thread_id)
        if message_count > 0:
            return
        twilio_response = await send_message(conversation.client_phone, DEFAULT_MESSAGE)
        if not twilio_response.status_code == httpx.codes.OK:
            logger.error("Error sending default message to client")
        try:
            message = Message()
            message.content = DEFAULT_MESSAGE
            message.conversation_id = conversation.id,
            message.sender_type = SenderTypeEnum.AGENT,
            message.user_id = 1
            save_message(message)
        except Exception as e:
            logger.error(f"Error while saving default message: {e}")
        conversations.end_conversation(conversation.id)
        end_conversation(conversation.conversation_id, conversation.client_phone)


@router.post("/webhook")
async def chatbot_webhook(request: Request):
    """
    Handles incoming webhook requests from the chatbot.

    Args:
    request (Request): The incoming request object.

    Returns:
    bool: True if the request is processed successfully, otherwise raises an HTTPException.
    """
    body = await request.json()
    logger.info(f"Message: {body}")
    thread_id: str = body.get('thread_id')
    media_url: str | None = body.get('media_url', None)
    media_dict = None
    conversation = conversations.get_conversation_by_thread_id(thread_id)
    notify_message = True
    conversation_id: int|None = None
    
    # If the conversation does not exist, create a new conversation and assign it to the user.
    if not conversation:
        notify_message = False
        conversations.create_conversation(body)
        await conversations.massive_asignation()
        conversation = conversations.get_conversation_by_thread_id(thread_id)
        if conversation:
            if conversation.state_id == ConversationStateEnum.CLOSED.value:
                logger.info(f"Webhook request ignored, conversation {conversation.id} already closed")
                return False
            conversation_id = conversation.id
            load_chatbot_messages(thread_id, conversation_id, body.get('message'))
            asyncio.create_task(send_default_message(thread_id))
    else:
        conversation_id = conversation.id
    if conversation.state_id == ConversationStateEnum.CLOSED.value:
        logger.info(f"Webhook request ignored, conversation {conversation_id} already closed")
        return False
    if media_url:
        media_dict = {
            'media_url': media_url
        }
    # Store message in database
    message, message_media = messages.save_message(Message(
        conversation_id=conversation_id,
        content=body.get('message'),
        sender_type=SenderTypeEnum.CLIENT,
        user=None
    ), conversation_id, media_dict)
    if not message:
        raise HTTPException(status_code=500, detail="Something went wrong")

    users_to_notify = users.get_user_ancestors(conversation.assigned_user_id)
    admin_users = users.get_all_users_by_role(role_id=UserRoleEnum.ADMIN.value)
    if users_to_notify:
        users_to_notify = users_to_notify + [user['id'] for user in admin_users if user['id'] not in users_to_notify]
    else:
        users_to_notify = [user['id'] for user in admin_users]
    # Setting message payload
    message_data = MessageData(
        conversation_id=message.conversation_id,
        content=message.content,
        created_at=message.created_at,
        sender_type=SenderType.CLIENT,
        phone_number=conversation.client_phone,
        user_id=None,
        attachment=media_url
    )

    if message_media:
        message_data.attachment_type = message_media.get('mime_type')
        message_data.attachment_name = message_media.get('filename')

    # Creating Notification object with the respective event
    notification = Notification(
        type=NotificationType.NEW_MESSAGE if notify_message else NotificationType.NEW_CONVERSATION,
        message=message_data
    )
    
    if users_to_notify:
        if (conversation.assigned_user_id):
            users_to_notify.append(conversation.assigned_user_id)
        for user_id in users_to_notify:
            await socket_manager.send_notification(user_id, notification)
        await socket_manager.send_message(conversation.id, message_data)
    
    return True