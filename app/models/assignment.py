import enum
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime, Column, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.utilities.db import Base


class AssignmentTypeEnum(enum.Enum):
    """
    Enumeration that defines the available assignment types in the system.

    Assignment types are used to categorize the different actions that can 
    be performed in relation to user assignments to conversations and events.

    Assignment Types:
        ASSIGNED (int): Represents a standard assignment of a user to a conversation or event.
        TRANSFERRED (int): Represents a transfer of an assignment from one user to another.
        INTERVENTION (int): Represents an intervention, which is restricted to supervisors and administrators only.
    """
    ASSIGNED = 1
    TRANSFERRED = 2
    INTERVENTION = 3 # Sólo para supervisores y administradores


class AssignmentType(Base):
    """
    Model that represents an assignment event type in the system.

    This model is used to define the different types of events that can be 
    associated with user assignments. Each event type has a unique identifier 
    and a code that represents it.

    Attributes:
        id (int): Unique identifier of the event type. It is the primary key of the table.
        code (str): Name of the event. It must be unique and is used to identify the type of event in the system.
    """
    __tablename__ = 'tbl_asignaciones_eventos'
    id = Column("evento_id", Integer, primary_key=True, index=True)
    code = Column("nombre_evento", String, unique=True, index=True)


class Assignment(Base):
    """
    Model that represents an assignment in the system.

    This model is used to manage user assignments to conversations and events.
    Each assignment is linked to a user, a conversation, and a specific event.

    Attributes:
        id (int): Unique identifier of the assignment. It is the primary key of the table.
        user_id (int): Identifier of the user to whom the conversation is assigned. 
                       It is a foreign key referencing the users table.
        conversation_id (int): Identifier of the conversation to which the user is assigned. 
                               It is a foreign key referencing the conversations table.
        event_id (int): Identifier of the event associated with the assignment. 
                         It is a foreign key referencing the assignment events table.
        created_at (datetime): Date and time when the assignment was created. 
                               It is automatically set at the time of creation.
        updated_at (datetime): Date and time of the last update to the assignment. 
                               It is automatically updated each time the assignment is modified.

    Relationships:
        user (User ): Relationship with the User model. Allows access to the details of the user 
                     associated with the assignment.
        conversation (Conversation): Relationship with the Conversation model. Allows access to 
                                      the details of the conversation associated with the assignment.
        event (AssignmentType): Relationship with the AssignmentType model. Allows access to the 
                                details of the event associated with the assignment.
    """
    __tablename__ = "tbl_asignaciones"
    id = Column("asignacion_id", Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column("usuario_id", ForeignKey("tbl_usuarios.usuario_id"))
    conversation_id: Mapped[int] = mapped_column(
        "conversacion_id", ForeignKey("tbl_conversaciones.id")
    )
    event_id: Mapped[int] = mapped_column("evento_id", ForeignKey("tbl_asignaciones_eventos.evento_id"))
    created_at: Mapped[DateTime] = mapped_column("fecha_creacion", DateTime, default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        "fecha_actualizacion", DateTime, default=func.now(), onupdate=func.now()
    )
    user = relationship("User", back_populates="assignments")
    conversation = relationship("Conversation", back_populates="assignments")
    event = relationship("AssignmentType")
    