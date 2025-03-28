import bcrypt
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from typing import List, Literal, Optional

from app.utilities.db import Base
from app.models.assignment import Assignment
from app.models.template import Template

from pydantic import BaseModel


child_relationship_kwargs = dict(foreign_keys="UsersGroup.child_id")
parent_relationship_kwargs = dict(foreign_keys="UsersGroup.parent_id")


class UserRoleEnum(enum.Enum):
    """Roles allowed for users in the platform.

    AGENT: Agent role.
    SUPERVISOR: Supervisor role.
    PRINCIPAL: Principal role.
    ADMIN: Admin role.
    """
    AGENT = 1
    SUPERVISOR = 2
    PRINCIPAL = 3
    ADMIN = 4
    SUPPORT = 5
    DATA_SECURITY = 6
    AUDIT = 7


class UserStateEnum(enum.Enum):
    """States for users in the platform.

    ONLINE: User is online.
    BREAK: User is on break.
    OFFLINE: User is offline.
    """
    ONLINE = 1
    BREAK = 2
    OFFLINE = 3


class UserRole(Base):
    """Class representing the User Role entity.

    Attributes:
        id (int): Unique identifier for the role.
        code (str): Name of the role.
        weight (int): Weight of the role.
    """
    __tablename__ = 'tbl_usuarios_roles'

    id = Column("rol_id", Integer, primary_key=True, index=True)
    code = Column("nombre_rol", String, unique=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
        }


class UserState(Base):
    """Class representing the User State entity.

    Attributes:
        id (int): Unique identifier for the state.
        code (str): Name of the state.
    """
    __tablename__ = 'tbl_usuarios_estados'

    id = Column("estado_id", Integer, primary_key=True, index=True)
    code = Column("nombre_estado", String, unique=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
        }


class CreateUser(BaseModel):
    """
    A model representing the data required to create a new user.

    Attributes:
        username (str): The username chosen by the user.
        full_name (str): The full name of the user.
        email (str): The email address of the user.
        role_id (int): The ID of the role assigned to the user.
        parent_id (Optional[int]): The ID of the parent user (optional).
    """
    username: str
    full_name: str
    email: str
    role_id: int
    parent_id: Optional[int] = None


class StatusEnum(str, enum.Enum):
    """
    An enumeration representing the possible statuses of a user.

    Attributes:
        ACTIVE (str): The user is active.
        INACTIVE (str): The user is inactive.
    """
    ACTIVE = "active"
    INACTIVE = "inactive"


class UpdateUserStatus(BaseModel):
    """
    A model representing the data required to update a user's status.

    Attributes:
        status (Literal[StatusEnum.ACTIVE, StatusEnum.INACTIVE]): The new status of the user.
    """
    status: Literal[
        StatusEnum.ACTIVE,
        StatusEnum.INACTIVE
    ]


class CreateUsersRelation(BaseModel):
    """
    A model representing the data required to create a new users relation.

    Attributes:
        child_id (int): The ID of the child user in the relation.

    Methods:
        None
    """
    child_id: int


class User(Base):
    """Class representing the User entity.

    Attributes:
        id (int): Unique identifier for the user.
        username (str): Username chosen by the user.
        full_name (str): Full name of the user.
        email (str): Email address of the user.
        password (str): Password for the user's account.
        role_id (int): Foreign key referencing the UserRole entity.
        state_id (int): Foreign key referencing the UserState entity.
        is_active (bool): Whether the user is active or not.
        created_at (DateTime): Timestamp when the user account was created.
        updated_at (DateTime): Timestamp when the user account was last updated.

    Relationships:
        role (UserRole): The role assigned to the user.
        state (UserState): The current state of the user.
        assignments (List[Assignment]): The assignments associated with the user.
        logs (List[UserLogs]): The logs associated with the user.
        templates (List[Template]): The templates associated with the user.
        associations_as_child (UsersGroup): The user's associations as a child.
        associations_as_parent (UsersGroup): The user's associations as a parent.

    Methods:
        set_password(password: str): Encrypts the password before saving it.
        check_password(password: str): Verifies if the provided password is correct.
    """

    __tablename__ = 'tbl_usuarios'

    id = Column("usuario_id", Integer, primary_key=True, index=True)
    username = Column("usuario", String, unique=True, index=True)
    full_name = Column("nombre", String)
    email = Column("correo", String, unique=True, index=True)
    password = Column("contrasena", String, nullable=True)
    role_id = Column("rol_id", Integer, ForeignKey('tbl_usuarios_roles.rol_id'))
    state_id = Column("estado_id", Integer, ForeignKey('tbl_usuarios_estados.estado_id'))
    is_active = Column("activo", Boolean, default=False)
    created_at = Column("fecha_creacion", DateTime, default=func.now())
    updated_at = Column("fecha_actualizacion", DateTime, default=func.now(), onupdate=func.now())

    role = relationship("UserRole", lazy='selectin')
    state = relationship("UserState")
    
    assignments: Mapped[List["Assignment"]] = relationship(back_populates="user")
    logs: Mapped[List["UserLogs"]] = relationship()
    templates: Mapped[List["Template"]] = relationship()

    associations_as_child = relationship('UsersGroup', back_populates='child', **child_relationship_kwargs)
    associations_as_parent = relationship('UsersGroup', back_populates='parent', **parent_relationship_kwargs)

    def set_password(self, password: str):
        """Encrypts the password before saving it.

        Args:
            password (str): The password to be encrypted.

        Returns:
            None
        """
        salt = bcrypt.gensalt()  # Generates a random salt
        self.password = bcrypt.hashpw(password.encode('utf-8'),
                                      salt).decode('utf-8')  # Saves the hash

    def check_password(self, password: str) -> bool:
        """Verifies if the provided password is correct.

        Args:
            password (str): The password to be verified.

        Returns:
            bool: True if the password is correct, False otherwise.
        """
        return bcrypt.checkpw(password.encode('utf-8'),
                              self.password.encode('utf-8'))


class UsersGroup(Base):
    """Class representing the UsersGroup entity.

    Attributes:
        id (int): Unique identifier for the users group.
        parent_id (int): Foreign key referencing the User entity as the parent.
        child_id (int): Foreign key referencing the User entity as the child.
        is_active (bool): Whether the users group is active or not.
        created_at (DateTime): Timestamp when the users group was created.
        updated_at (DateTime): Timestamp when the users group was last updated.

    Relationships:
        parent (User): The parent user in the users group.
        child (User): The child user in the users group.

    Methods:
        None
    """
    __tablename__ = "tbl_usuarios_jerarquias"
    id = Column("jerarquia_id", Integer, primary_key=True, index=True)
    parent_id: Mapped[int] = mapped_column("jefe_usuario_id", ForeignKey("tbl_usuarios.usuario_id"))
    child_id: Mapped[int] = mapped_column("dependiente_usuario_id", ForeignKey("tbl_usuarios.usuario_id"))
    is_active: Mapped[bool] = mapped_column("estado")
    created_at: Mapped[DateTime] = mapped_column("fecha_creacion", DateTime, default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        "fecha_actualizacion", DateTime, default=func.now(), onupdate=func.now()
    )
    parent = relationship("User", back_populates='associations_as_parent', **parent_relationship_kwargs)
    child = relationship("User", back_populates='associations_as_child', **child_relationship_kwargs)


class EventTypesEnum(enum.Enum):
    """Event types for users in the platform.

    Attributes:
        STATE_CHANGE (int): Event type for state change.
        TRANSFER (int): Event type for transfer.
        END_CHAT (int): Event type for end chat.

    Methods:
        None
    """
    """Event types for users in the platform"""
    STATE_CHANGE = 1
    TRANSFER = 2
    END_CHAT = 3


class EventTypes(Base):
    """Class representing the EventTypes entity.

    Attributes:
        id (int): Unique identifier for the event type.
        code (str): Name of the event type.

    Relationships:
        None

    Methods:
        None
    """
    __tablename__ = "tbl_usuarios_logs_eventos"

    id = Column("evento_id", Integer, primary_key=True, index=True)
    code = Column("nombre_evento", String, unique=True, index=True)


class UserLogs(Base):
    """Class representing the UserLogs entity.

    Attributes:
        id (int): Unique identifier for the user log.
        user_id (int): Foreign key referencing the User entity.
        event_type (int): Foreign key referencing the EventTypes entity.
        event_details (str): Details of the event.
        created_at (DateTime): Timestamp when the user log was created.

    Relationships:
        user (User): The user associated with the user log.

    Methods:
        None
    """
    __tablename__ = 'tbl_usuarios_logs'

    id = Column("log_id", Integer, primary_key=True, index=True)
    user_id = Column("usuario_id", Integer, ForeignKey('tbl_usuarios.usuario_id'))
    user = relationship('User', back_populates='logs')
    event_type = Column("evento_id", Integer, ForeignKey("tbl_usuarios_logs_eventos.evento_id"))
    type = relationship('EventTypes')
    event_details = Column("detalle_evento", String)
    created_at = Column("fecha_creacion", DateTime, default=func.now())