from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.utilities.db import Base


class MimeTypes(enum.Enum):
    """
    Enumeration that defines the various MIME types used in the system.

    This enumeration is used to categorize different file types based on their 
    MIME (Multipurpose Internet Mail Extensions) types, which indicate the nature 
    and format of a file.

    MIME Types:
        JPG (str): Represents JPEG image files.
        JPEG (str): Represents JPEG image files.
        PNG (str): Represents PNG image files.
        PDF (str): Represents PDF document files.
        WORD (str): Represents Microsoft Word document files (pre-2007).
        WORD2003 (str): Represents Microsoft Word document files (2007 and later).
    """
    JPG = "image/jpg"
    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"
    WORD = "application/msword"
    WORD2003 = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class MessageMedia(Base):
    """
    Model that represents media files associated with messages in the system.

    This model is used to manage the media files that can be attached to messages. 
    Each media file has a unique identifier, filename, URL, MIME type, size, 
    sender information, and creation timestamp.

    Attributes:
        id (int): Unique identifier of the media file. It is the primary key of the table.
        filename (str): Name of the media file.
        url (str): URL where the media file is stored.
        mime_type (str): MIME type of the media file, indicating its format.
        size (float): Size of the media file in bytes.
        sender (str): Identifier of the sender of the media file.
        created_at (datetime): Date and time when the media file was created. 
                               It is automatically set at the time of creation.

    Relationships:
        message (Message): Relationship with the Message model. 
                           Allows access to the message associated with the media file.
    """
    __tablename__ = 'tbl_archivos_adjuntos'

    id = Column("archivo_id", Integer, primary_key=True, index=True)
    filename = Column("nombre_archivo", String)
    url = Column(Text)
    mime_type = Column("metatipo", String)
    size = Column("tamano", Float)
    sender = Column("remitente", String)
    created_at = Column("fecha_creacion", DateTime, server_default=func.now())
    
    # Relación con el mensaje
    message = relationship("Message", back_populates="message_media")

    def to_dict(self):
        """
        Convert the MessageMedia instance to a dictionary representation.

        Returns:
            dict: A dictionary containing the filename, URL, MIME type, and size of the media file.
        """
        return {
            'filename': self.filename,
            'url': self.url,
            'mime_type': self.mime_type,
            'size': self.size,
        }