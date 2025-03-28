from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.sql import func

from app.utilities.db import Base
from pydantic import BaseModel, field_serializer

from datetime import datetime
from typing import Optional


class CreateTemplate(BaseModel):
    """
    A Pydantic model representing the data required to create a new template.

    Attributes:
    user_id (Optional[int]): The ID of the user creating the template. Defaults to None.
    content (str): The content of the template.
    """
    user_id: Optional[int] = None
    content: str

class UpdateTemplate(BaseModel):
    """
    A Pydantic model representing the data required to update an existing template.

    Attributes:
    content (str): The updated content of the template.
    is_active (Optional[bool]): A flag indicating whether the template is active or not. Defaults to None.
    """
    content: str
    is_active: Optional[bool] = None

class TemplateInDB(BaseModel):
    """
    A Pydantic model representing a template stored in the database.

    Attributes:
    id (int): The unique ID of the template.
    user_id (Optional[int]): The ID of the user who created the template. Defaults to None.
    content (str): The content of the template.
    is_active (bool): A flag indicating whether the template is active or not.
    created_at (datetime): The timestamp when the template was created.
    updated_at (datetime): The timestamp when the template was last updated.
    """
    id: int
    user_id: Optional[int] = None
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime):
        """
        A method to serialize datetime objects to ISO format.

        Args:
        value (datetime): The datetime object to be serialized.

        Returns:
        str: The serialized datetime in ISO format.
        """
        return value.isoformat()

    class Config:
        from_attributes = True


class Template(Base):
    """
    A SQLAlchemy model representing a template in the database.

    Attributes:
    id (int): The unique ID of the template.
    user_id (Optional[int]): The ID of the user who created the template. Defaults to None.
    content (str): The content of the template.
    is_active (bool): A flag indicating whether the template is active or not.
    created_at (datetime): The timestamp when the template was created.
    updated_at (datetime): The timestamp when the template was last updated.
    """
    __tablename__ = 'tbl_plantillas'

    id = Column("plantilla_id", Integer, primary_key=True, index=True)
    user_id = Column("usuario_id", Integer, ForeignKey('tbl_usuarios.usuario_id'), nullable=True)
    content = Column("contenido", Text)
    is_active = Column("activo", Boolean, default=True)
    created_at = Column("fecha_creacion", DateTime, server_default=func.now())
    updated_at = Column("fecha_actualizacion", DateTime, server_default=func.now(), onupdate=func.now())

    def update(self, **kwargs):
        """
        A method to update the template with the provided keyword arguments.

        Args:
        **kwargs: The keyword arguments containing the updated values.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)