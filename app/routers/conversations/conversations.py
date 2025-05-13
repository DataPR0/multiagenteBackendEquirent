import base64
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from app.helpers import conversations, messages
from app.utilities.logger import logger
from app.helpers.conversations import set_uncount_messages, get_conversation_by_id
from app.helpers.users import assign_conversation_to_agent, get_user_by_id, get_user_ancestors, get_all_users_by_role
from app.helpers.twilio import send_message as send_msg_twilio
from app.helpers.twilio import end_conversation as end_chatbot
from app.models.assignment import AssignmentTypeEnum
from app.models.message import Message, SenderTypeEnum
from app.models.conversation import Conversation, ConversationStateEnum
from app.models.websockets import Notification, NotificationType, MessageData, SenderType, ConversationData
from app.models.user import UserRoleEnum
from app.utilities.socket import socket_manager

router = APIRouter()


@router.get("", status_code=201)
async def get_all_conversations(
    request: Request, 
    user_id: str = None
) -> list[dict]:
    """
    Retrieves all conversations for a given user.

    Args:
    - request (Request): The incoming request.
    - user_id (str, optional): The ID of the user. Defaults to None.

    Returns:
    - dict: A dictionary containing the conversations.
    """
    user = request.state.current_user
    response = conversations.get_all_conversations(user_id=user.id, user_selected_id=user_id)
    return response


@router.get("/{id}")
async def get_conversation_messages(
    id: int, 
    request: Request
) -> dict:
    """
    Retrieves all messages for a given conversation.

    Args:
    - id (str): The ID of the conversation.
    - request (Request): The incoming request.

    Returns:
    - dict: A dictionary containing the conversation details and messages.
    """
    user = request.state.current_user
    conversation = conversations.get_conversation_by_id(id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = messages.get_all_messages_by_conversation(id)
    if user.id == conversation.assigned_user_id:
        set_uncount_messages(id, 0)
    response = {
        'detail': conversation.to_dict(),
        'messages': msgs
    }
    
    return response


@router.post("/{id}")
async def send_message(
    id: int, 
    request: Request
) -> dict:
    """
    Sends a message in a conversation.

    Args:
    - id (int): The ID of the conversation.
    - request (Request): The incoming request.

    Returns:
    - dict: A dictionary containing the sent message and media.
    """
    try:
        body = await request.form()
        files: list[UploadFile|None] = body.getlist("files")
        user = request.state.current_user
        user_id = user.id
        user_name = None
        if user.role_id != UserRoleEnum.ADMIN.value:
            user_name = user.full_name
        conversation = conversations.get_conversation_by_id(id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.state_id == ConversationStateEnum.CLOSED.value:
            raise HTTPException(status_code=404, detail="Conversation was finished")
        if conversation.state_id == ConversationStateEnum.PENDING.value and user.role_id == UserRoleEnum.AGENT.value:
            raise HTTPException(status_code=404, detail="Conversation is not assigned to you")
        message_text = body.get("message")
        response_msgs = {
            'status': False,
            'data': []
        }
        if not len(files):
            files = [None]
        for i, _file in enumerate(files):
            media_content = await _file.read() if _file else None
            media_dict = None
            if (media_content):
                media_dict = {}
                media_dict['media_url'] = base64.b64encode(media_content).decode("utf-8")
                media_dict['filename'] = _file.filename
                media_dict['mime_type'] = _file.content_type
                media_dict['size'] = len(media_content)

            message = Message()
            message.content = message_text if message_text and i == 0 else ""
            message.conversation_id = id
            message.sender_type = SenderTypeEnum.AGENT
            message.user_id = user_id
            message_obj, message_media = messages.save_message(message, id, media_dict)
            # print(message_obj, message_media)
            if message_obj:
                response = await send_msg_twilio(conversation.client_phone, body.get("message"), media_dict, user_name)
            # Send message to users up in the hierarchy based on assigned user
            users_to_notify = get_user_ancestors(conversation.assigned_user_id)
            admin_users = get_all_users_by_role(role_id=UserRoleEnum.PRINCIPAL.value)
            if users_to_notify:
                users_to_notify = users_to_notify + [user['id'] for user in admin_users if user['id'] not in users_to_notify]
            else:
                users_to_notify = [user['id'] for user in admin_users]
            
            msg_data = MessageData(
                content=message.content,
                created_at=datetime.now(),
                conversation_id=id,
                user_id=user_id,
                user_name=user.full_name,
                sender_type=SenderType.AGENT
            )
            # If connected user is not the assigned user, send notification to assigned user
            if conversation.assigned_user_id:
                users_to_notify.append(conversation.assigned_user_id)
            for ancestor_id in users_to_notify:
                await socket_manager.send_notification(ancestor_id, Notification(
                    type=NotificationType.NEW_MESSAGE,
                    message=msg_data
                ))
            await socket_manager.send_message(conversation.id, msg_data)
            response_msgs["data"].append({
                'message': message_obj.to_dict(),
                'media': message_media
            })
        response_msgs["status"] = True
        # print(response_msgs)
        return response_msgs
    except KeyError as e:
        logger.error(e)
    except Exception as e:
        logger.error(e)
        raise e
    return response_msgs


@router.post("/{id}/transfer")
async def transfer_conversation(id: int, request: Request):
    """
    Transfers a conversation to another agent.

    Args:
    - id (int): The ID of the conversation.
    - request (Request): The incoming request.

    Returns:
    - dict: A dictionary containing the result of the transfer operation.
    """
    body = await request.json()
    session_user = request.state.current_user
    if 'user_id' not in body:
        raise HTTPException(status_code=400, detail="There are missing parameters in the payload.")
    conversation_obj = get_conversation_by_id(id)
    if not conversation_obj:
        raise HTTPException(status_code=404, detail="Conversation doesn't exist.")
    response = await assign_conversation_to_agent(
        id, body.get("user_id"),
        session_user,
        AssignmentTypeEnum.TRANSFERRED.value
    )
    if response.success:
        await conversations.massive_asignation()
    return response


@router.post("/{id}/endChat")
async def end_conversation(id: int, request: Request):
    """
    Ends a conversation.

    Args:
    - id (int): The ID of the conversation.
    - request (Request): The incoming request.

    Returns:
    - dict: A dictionary containing the result of the end conversation operation.
    """
    body = await request.json()
    conversation_obj = conversations.get_conversation_by_id(id)
    session_user = request.state.current_user
    assigned_user = get_user_by_id(conversation_obj.assigned_user_id)
    if conversations.unable_end_conversation_conditional(assigned_user, session_user):
        return HTTPException(status_code=403, detail="You can't finish this conversation")
    
    typification_data = {
        "conversation": conversation_obj.to_dict(),
        "motive": body.get('motive'),
        "comment": body.get('filteredSubcategorias', ""),
        "client_id": body.get('client_id'),
    }
    
    agent_name = session_user.full_name if not assigned_user else assigned_user.full_name
    
    response = conversations.end_conversation(
        conversation_obj.id,
        typification_data, 
        request.state.current_user
    )
    
    if response:
        chatbot_response = await end_chatbot(
            conversation_obj.conversation_id, 
            conversation_obj.client_phone, 
            agent_name
        )
        if (chatbot_response.status_code == 200):
            await conversations.massive_asignation()
    message_data = MessageData(
        conversation_id=id,
        content="##EndChat##",
        created_at=conversation_obj.updated_at,
        sender_type=SenderType.AGENT
    )
    users_to_notify = get_user_ancestors(conversation_obj.assigned_user_id)
    admin_users = get_all_users_by_role(role_id=UserRoleEnum.PRINCIPAL.value)
    if users_to_notify:
        users_to_notify = users_to_notify + [user['id'] for user in admin_users if user['id'] not in users_to_notify]
    else:
        users_to_notify = [user['id'] for user in admin_users]
    # Creating Notification object with the respective event
    notification = Notification(
        type=NotificationType.END_CONVERSATION,
        message=message_data
    )
    # If connected user is not the assigned user, send notification to assigned user
    if conversation_obj.assigned_user_id:
        users_to_notify.append(conversation_obj.assigned_user_id)
    for ancestor_id in users_to_notify:
        await socket_manager.send_notification(ancestor_id, notification)
    await socket_manager.send_message(id, message_data)
    return response


@router.post("/{id}/reset-unread-count")
async def reset_unread_count(id: int) -> dict:
    set_uncount_messages(id, 0)
    conversation_obj = conversations.get_conversation_by_id(id)
    users_to_notify = get_user_ancestors(conversation_obj.assigned_user_id)
    admin_users = get_all_users_by_role(role_id=UserRoleEnum.PRINCIPAL.value)
    if users_to_notify:
        users_to_notify = users_to_notify + [user['id'] for user in admin_users if user['id'] not in users_to_notify]
    else:
        users_to_notify = [user['id'] for user in admin_users]
    # Creating Notification object with the respective event
    notification = Notification(
        type=NotificationType.MESSAGES_READ,
        conversation=ConversationData(
            id=conversation_obj.id,
            client_phone=conversation_obj.client_phone,
            last_message=conversation_obj.last_message,
            unread_count=conversation_obj.unread_count,
            updated_at=conversation_obj.updated_at,
            user_id=conversation_obj.assigned_user_id,
            state_id=conversation_obj.state_id
        )
    )
    for user_id in users_to_notify:
        if conversation_obj.assigned_user_id == user_id:
            continue
        await socket_manager.send_notification(user_id, notification)
    return JSONResponse(status_code=200, content={"success": True})
