from pydantic import BaseModel, Field, field_serializer
from enum import Enum
from typing import Literal, Optional
from datetime import datetime


class NotificationType(str, Enum):
    """
    Enum for notification types.

    Attributes:
        NEW_CONVERSATION (str): New conversation notification.
        NEW_TRANSFER (str): New transfer notification.
        NEW_MESSAGE (str): New message notification.
        END_CONVERSATION (str): End conversation notification.
    """
    NEW_CONVERSATION = "new_conversation"
    NEW_TRANSFER = "new_transfer"
    NEW_MESSAGE = "new_message"
    END_CONVERSATION = "end_conversation"
    MESSAGES_READ = "messages_read"

class SenderType(int, Enum):
    """
    Enum for sender types.

    Attributes:
        AGENT (int): Agent sender type.
        CHATBOT (int): Chatbot sender type.
        CLIENT (int): Client sender type.
    """
    AGENT = 1
    CHATBOT = 2
    CLIENT = 3


class ConversationData(BaseModel):
    """
    Model for conversation data.

    Attributes:
        id (int): Conversation ID.
        client_phone (str): Client phone number.
        last_message (str): Last message in the conversation.
        unread_count (int): Number of unread messages.
        updated_at (datetime): Last update time.
        user_id (int): User ID.
        state_id (int): State ID.
        previous_user (Optional[int]): Previous user ID.
    """
    id: int = Field(...)
    client_phone: str = Field(...)
    last_message: str = Field(...)
    unread_count: int = Field(...)
    updated_at: datetime = Field(...)
    user_id: int = Field(...)
    state_id: int = Field(...)
    previous_user: Optional[int] = None 

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime) -> str:
        """
        Serialize updated_at field to ISO format.

        Args:
            value (datetime): Updated at value.

        Returns:
            str: ISO formatted updated at value.
        """
        return value.isoformat()


class MessageData(BaseModel):
    """
    Model for message data.

    Attributes:
        content (str): Message content.
        conversation_id (int): Conversation ID.
        created_at (datetime): Creation time.
        user_id (Optional[int]): User ID.
        user_name (Optional[str]): User name.
        phone_number (Optional[str]): Phone number.
        state_id (Optional[int]): State ID.
        attachment (Optional[str]): Attachment.
        attachment_type (Optional[str]): Attachment type.
        attachment_name (Optional[str]): Attachment name.
        sender_type (Literal[SenderType.AGENT, SenderType.CHATBOT, SenderType.CLIENT]): Sender type.
    """
    content: str = Field(...)
    conversation_id: int = Field(...)
    created_at: datetime = Field(...)
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    phone_number: Optional[str] = None
    state_id: Optional[int] = None
    attachment: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_name: Optional[str] = None
    sender_type: Literal[
        SenderType.AGENT,
        SenderType.CHATBOT,
        SenderType.CLIENT
    ]
    

    @field_serializer("created_at")
    def serialize_datetime(self, value: datetime) -> str:
        """
        Serialize created_at field to ISO format.

        Args:
            value (datetime): Created at value.

        Returns:
            str: ISO formatted created at value.
        """
        return value.isoformat()


class StatusData(BaseModel):
    """
    Model for status data.

    Attributes:
        success (bool): Success status.
        message (str): Status message.
    """
    success: bool = Field(...)
    message: str = Field(...)


class Notification(BaseModel):
    """
    Model for notification.

    Attributes:
        type (Literal[NotificationType.NEW_CONVERSATION, NotificationType.NEW_TRANSFER, NotificationType.NEW_MESSAGE, NotificationType.END_CONVERSATION]): Notification type.
        conversation (Optional[ConversationData]): Conversation data.
        message (Optional[MessageData]): Message data.
    """
    type: Literal[
        NotificationType.NEW_CONVERSATION,
        NotificationType.NEW_TRANSFER,
        NotificationType.NEW_MESSAGE,
        NotificationType.END_CONVERSATION,
        NotificationType.MESSAGES_READ
    ]
    conversation: Optional[ConversationData] = None
    message: Optional[MessageData] = None


class ChatWebSocketResponseType(str, Enum):
    """
    Enum for chat WebSocket response types.

    Attributes:
        STATUS (str): Status response type.
        MESSAGE (str): Message response type.
    """
    STATUS = "status"
    MESSAGE = "message"


class ChatWebSocketResponse(BaseModel):
    """
    Model for chat WebSocket response.

    Attributes:
        type (Literal[ChatWebSocketResponseType.MESSAGE, ChatWebSocketResponseType.STATUS]): Response type.
        status (Optional[StatusData]): Status data.
        message (Optional[MessageData]): Message data.
    """
    type: Literal[
        ChatWebSocketResponseType.MESSAGE,
        ChatWebSocketResponseType.STATUS
    ]
    status: Optional[StatusData] = None
    message: Optional[MessageData] = None