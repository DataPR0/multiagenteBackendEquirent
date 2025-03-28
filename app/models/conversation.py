from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.sql import func
from typing import List
import enum

from app.utilities.db import Base
from app.models.assignment import Assignment


class ConversationStateEnum(enum.Enum):
    """
    Enumeration that defines the possible states of a conversation.

    Conversation states are used to track the current status of a conversation 
    within the system.

    Conversation States:
        PENDING (int): The conversation is not yet assigned.
        OPEN (int): The conversation is assigned and in progress with an agent.
        CLOSED (int): The process has been completed.
    """
    PENDING = 1     # Sin Asignar
    OPEN = 2        # Asignado y en proceso con agente
    CLOSED = 3      # Proceso finalizado


class ConversationState(Base):
    """
    Model that represents the state of a conversation in the system.

    This model is used to define the different states that a conversation can 
    have. Each state has a unique identifier and a code that represents it.

    Attributes:
        id (int): Unique identifier of the conversation state. It is the primary key of the table.
        code (str): Name of the state. It must be unique and is used to identify the state in the system.
    """
    __tablename__ = 'tbl_conversaciones_estados'
    id = Column("estado_id", Integer, primary_key=True, index=True)
    code = Column("nombre_estado", String, unique=True, index=True)


class Conversation(Base):
    """
    Model that represents a conversation in the system.

    This model is used to manage conversations between clients and agents. 
    Each conversation is linked to a client, an assigned user, and has a 
    specific state.

    Attributes:
        id (int): Unique identifier of the conversation. It is the primary key of the table.
        conversation_id (str): Unique identifier of the conversation in the system.
        client_phone (str): Phone number associated with the client.
        assigned_user_id (int): Identifier of the user assigned to the conversation. 
                                It is a foreign key referencing the users table.
        credit_number (str): Selected credit number associated with the conversation.
        unread_count (int): Number of unread messages in the conversation. Defaults to 0.
        state_id (int): Identifier of the state associated with the conversation. 
                         It is a foreign key referencing the conversation states table.
        last_message (str): The last message sent in the conversation.
        created_at (datetime): Date and time when the conversation was created. 
                               It is automatically set at the time of creation.
        updated_at (datetime): Date and time of the last update to the conversation. 
                               It is automatically updated each time the conversation is modified.

    Relationships:
        assigned_user (User ): Relationship with the User model. Allows access to the user 
                              assigned to the conversation.
        assignments (List[Assignment]): Relationship with the Assignment model. 
                                         Allows access to the assignments related to the conversation.
        state (ConversationState): Relationship with the ConversationState model. 
                                   Allows access to the state associated with the conversation.
        messages (List[Message]): Relationship with the Message model. 
                                   Allows access to the messages associated with the conversation.
        typification (Typification): Relationship with the Typification model. 
                                     Allows access to the typification associated with the conversation.
    """
    __tablename__ = 'tbl_conversaciones'

    id = Column("id", Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column("conversacion_id", String, index=True)
    client_phone = Column("telefono_asociado", String)
    assigned_user_id = Column("usuario_id", Integer, ForeignKey('tbl_usuarios.usuario_id'), nullable=True)
    credit_number = Column("numero_credito_seleccionado", String)
    unread_count = Column("mensajes_no_leidos", Integer, default=0)
    state_id = Column("estado_id", Integer, ForeignKey("tbl_conversaciones_estados.estado_id"))
    last_message = Column("ultimo_mensaje", String)
    created_at = Column("fecha_creacion", DateTime, default=func.now())
    updated_at = Column("fecha_ultimo_mensaje", DateTime, default=func.now(), onupdate=func.now())

    # Relationship With User
    assigned_user = relationship("User")
    assignments: Mapped[List["Assignment"]] = relationship(back_populates="conversation")

    # Relationship With ConversationState
    state = relationship("ConversationState")

    # Relationship With Message
    messages = relationship("Message", back_populates="conversation")

    # Relationship With Typification
    typification = relationship("Typification", back_populates="conversation")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "client_phone": self.client_phone,
            "assigned_user_id": self.assigned_user_id,
            "credit_number": self.credit_number,
            "unread_count": self.unread_count,
            "state_id": self.state_id,
            "last_message": self.last_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            }