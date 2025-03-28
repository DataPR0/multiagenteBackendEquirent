from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Text, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.utilities.db import Base


class Typification(Base):
    """
    Represents a typification in the database.

    Attributes:
        id (int): Unique identifier for the typification.
        conversation_id (int): Foreign key referencing the conversation ID.
        motive (str): Motive for the typification.
        comment (str): Comment for the typification.
        credit_number (str): Credit number associated with the typification.
        client_id (str): Client ID associated with the typification.
        created_at (datetime): Timestamp when the typification was created.

    Relationships:
        conversation (Conversation): Relationship with the conversation table.
    """
    __tablename__ = 'tbl_tipificaciones'

    id = Column("tipificacion_id", Integer, primary_key=True, index=True)
    conversation_id = Column("conversacion_id", Integer, ForeignKey('tbl_conversaciones.id'))
    motive = Column("motivo", String)
    comment = Column("comentario", Text)
    credit_number = Column("numero_credito", String)
    client_id = Column("documento", String)
    created_at = Column("fecha_creacion", DateTime, server_default=func.now())

    # Relación con la conversación
    conversation = relationship("Conversation", back_populates="typification")
