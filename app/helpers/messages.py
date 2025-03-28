from contextlib import closing
from app.helpers.message_media import detect_mime_type
from app.models.conversation import Conversation
from app.models.message import Message, SenderTypeEnum
from app.models.message_media import MessageMedia
from app.models.user import User
from app.utilities.db import get_session
from app.utilities.socket import socket_manager
from sqlalchemy import select


def save_message(message: Message, conversation_id: int|str, media_dict: dict = None) -> tuple[Message, dict | None]:
    """
    Saves a message to the database.

    Args:
    - message (Message): The message to be saved.
    - conversation_id (int|str): The ID of the conversation the message belongs to.
    - media_dict (dict, optional): A dictionary containing media information. Defaults to None.

    Returns:
    - tuple[Message, dict | None]: A tuple containing the saved message and the media information as a dictionary, or None if an error occurs.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            message_media = None
            conversation: Conversation|None = None
            if isinstance(conversation_id, int):
                conversation = session.query(Conversation).filter(
                    Conversation.id==conversation_id
                ).first()
            elif isinstance(conversation_id, str):
                conversation = session.query(Conversation).filter(
                    Conversation.conversation_id==conversation_id
                ).first()
            conversation.last_message = "Archivo adjunto" if media_dict else message.content
            if unread_conditional(message, conversation):
                conversation.unread_count += 1
            if (media_dict):
                media_url = media_dict.get('media_url', None)
                mime_type = media_dict.get('mime_type', None)
                if (mime_type is None):
                    file_data = detect_mime_type(media_url)
                else:
                    file_data = [
                        media_dict.get('filename'),
                        media_dict.get('mime_type'),
                        media_dict.get('size',-1)
                    ]
                if file_data and media_url:
                    message_media = MessageMedia(
                        filename=file_data[0],
                        url=media_url,
                        mime_type=file_data[1],
                        size=file_data[2],
                        sender=SenderTypeEnum.CLIENT.value,
                    )
                    session.add(message_media)
                    session.commit()
                    session.refresh(message_media)
                    message.message_media_id = message_media.id
            conversation.last_message = 'Archivo adjunto' if not message.content and message_media else message.content
            session.add(message)
            session.commit()
            session.refresh(message)
            response = message, message_media.to_dict() if message_media else None
            session.close()
            return response
    except Exception as e:
        print(f"Error saving message: {e}")
    return None, None


def get_all_messages_by_conversation(id: str) -> list[dict] | None:
    """
    Retrieves all messages from a conversation.

    Args:
    - id (str): The ID of the conversation.

    Returns:
    - list[dict] | None: A list of dictionaries containing message information, or None if an error occurs.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            messages_list_query = select(
                Message,
                User.full_name.label('user_name'),
                MessageMedia.url.label('attachment'),
                MessageMedia.mime_type.label('attachment_type'),
                MessageMedia.filename.label('attachment_name'),
            ).join(
                User,
                User.id == Message.user_id, isouter=True
            ).join(
                MessageMedia,
                Message.message_media_id == MessageMedia.id,
                isouter=True
            ).filter(
                Message.conversation_id==id
            ).order_by(Message.created_at)
            messages_list = session.execute(messages_list_query).all()
            messages_list_transformed = [
                {
                    "id": message.id,
                    "content": message.content,
                    "created_at": message.created_at,
                    "sender_type": message.sender_type,
                    "user_name": user_name,
                    "attachment": attachment,
                    "attachment_type": attachment_type,
                    "attachment_name": attachment_name
                }
                for message, user_name, attachment, attachment_type, attachment_name in messages_list
            ]
            session.close()
            return messages_list_transformed
    except Exception as e:
        print(f"Error getting messages: {e}")
    return None


def delete_message(message_id: int) -> bool:
    """
    Deletes a message from the database.

    Args:
    - message_id (int): The ID of the message to be deleted.

    Returns:
    - bool: True if the message is deleted successfully, False otherwise.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            session.query(Message).filter(Message.id==message_id).delete()
            session.commit()
            session.close()
    except Exception as e:
        print(f"Error deleting message: {e}")
        return False
    return True


def unread_conditional(message: Message, conversation: Conversation) -> bool:
    """
    Checks if a message is unread.

    Args:
    - message (Message): The message to be checked.
    - conversation (Conversation): The conversation the message belongs to.

    Returns:
    - bool: True if the message is unread, False otherwise.
    """
    conversation_id = message.conversation_id
    user_id = conversation.assigned_user_id
    try:
        return message.user_id is None and (
            conversation_id not in socket_manager.conversations or
            user_id not in socket_manager.conversations[conversation_id])
    except KeyError as e:
        return True
    except Exception as e:
        print(f"Error checking if message is unread: {e}")
        return False