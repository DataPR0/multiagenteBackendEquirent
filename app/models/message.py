from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.utilities.db import Base
import enum


class SenderTypeEnum(enum.Enum):
    """
    Enum representing the type of sender.

    Attributes:
        CHATBOT (int): The message was sent by a chatbot.
        AGENT (int): The message was sent by an agent.
        CLIENT (int): The message was sent by a client.
    """
    CHATBOT = 1
    AGENT = 2
    CLIENT = 3


class Message(Base):
    """
    Represents a message in the database.

    Attributes:
        id (int): The unique identifier of the message.
        content (str): The content of the message.
        created_at (datetime): The date and time the message was created.
        conversation_id (int): The identifier of the conversation the message belongs to.
        sender_type (SenderTypeEnum): The type of sender.
        user_id (int): The identifier of the user who sent the message (optional).
        message_media_id (int): The identifier of the media attached to the message (optional).

    Relationships:
        message_media (MessageMedia): The media attached to the message (optional).
        conversation (Conversation): The conversation the message belongs to.
        user (User): The user who sent the message.
    """
    __tablename__ = 'tbl_mensajes'

    id = Column("mensaje_id", Integer, primary_key=True, index=True)
    content = Column("contenido", Text)
    created_at = Column("fecha_creacion", DateTime, server_default=func.now())
    conversation_id = Column("conversacion_id", Integer, ForeignKey('tbl_conversaciones.id'))
    sender_type = Column("remitente", Enum(SenderTypeEnum))
    user_id = Column("usuario_id", Integer, ForeignKey('tbl_usuarios.usuario_id'), nullable=True)
    message_media_id = Column("archivo_id", Integer, ForeignKey('tbl_archivos_adjuntos.archivo_id'))

    # Relación con archivo (opcional)
    message_media = relationship("MessageMedia")
    # Relación con la conversación
    conversation = relationship("Conversation", back_populates="messages")
    # Relación con el usuario
    user = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "conversation_id": self.conversation_id,
            "sender_type": self.sender_type.name,
            "user_id": self.user_id,
            "message_media_id": self.message_media_id
        }