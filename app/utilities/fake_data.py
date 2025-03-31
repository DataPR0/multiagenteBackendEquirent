from app.utilities.db import get_session
from app.models.user import User, UserRole, UsersGroup
from app.models.conversation import Conversation, ConversationState
from app.models.message import Message, SenderTypeEnum
from app.models.template import Template
from passlib.context import CryptContext
from contextlib import closing
from sqlalchemy import text
from sqlalchemy import create_engine
from app.config import settings
from app.utilities.logger import logger
from app.utilities.db import initialize_database

from faker import Faker

import os
import uuid
import json

cd = os.path.dirname(os.path.abspath(__file__))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def load_admin():
    """
    Creates an admin user in the database if it does not exist.
    
    Generates a random password and securely stores it.
    
    Returns:
        None
    """
    faker = Faker()
    with closing(next(get_session("multiagent"))) as session:
        users_count = session.query(User).count()
        if users_count > 0:
            logger.info("Admin user already exists")
            return
        admin_role = session.query(UserRole).filter(UserRole.code == "ADMIN").first()
        random_pwsd = faker.password()
        logger.info(f"Admin password: {random_pwsd}")
        admin = User(
            username="admin",
            full_name="Administrador",
            email=settings.smtp_sender,
            password=pwd_context.hash(random_pwsd),
            role=admin_role,
            is_active=True
        )
        session.add(admin)
        session.commit()
    logger.info("Admin user created")
    
def load_default_data() -> bool:
    """
    Loads default data into the database from an SQL file.
    
    Returns:
        bool: True if the data was loaded successfully, False otherwise.
    """
    engine = create_engine(settings.sqlite_uri)
    try:
        with open("app/utilities/default.sql") as file:
            with engine.begin() as conn:
                dbapi_conn = conn.connection
                dbapi_conn.executescript(file.read())
    except Exception as e:
        logger.error(f"Error loading default data: {e}")
        return False
    logger.info("Default data loaded")
    return True


def load_users() -> tuple[int, int]:
    """
    Loads users from a JSON file into the database.
    
    If users already exist, no more are loaded.
    
    Returns:
        Tuple[int, int]: A tuple containing the start and end indices of the created users.
    """
    with closing(next(get_session("multiagent"))) as session:
        # Check if users already exist
        count = session.query(User).count()
        if count > 1:
            logger.info("Users already exist")
            return 0, 0
        users_list_path = cd + "/users.json"
        if not os.path.exists(users_list_path):
            logger.info("Users file not found")
            return 0, 0
        with open(cd + "/users.json", "r", encoding="utf-8") as file:
            users = json.load(file)
        subordinates = {}
        agents_start = 0
        agents_end = 0
        for index, user_dict in enumerate(users):
            if user_dict.get("role") == "AGENT" and agents_start == 0:
                agents_start = index
            if user_dict.get("role") == "AGENT":
                agents_end = index
            exists = session.query(User).filter(User.username == user_dict.get("username")).first()
            role = session.query(UserRole).filter(UserRole.code == user_dict.get("role")).first()
            if exists is None:
                user = User(
                    username=user_dict.get('username'),
                    full_name=user_dict.get('full_name'),
                    email=user_dict.get('email'),
                    password=pwd_context.hash(user_dict.get('password')),
                    role_id=role.id,
                    is_active=True
                )
                session.add(user)
            else:
                logger.info(f"User with username {user_dict.get('username')} already exists")
            if "subordinates" in user_dict.keys():
                for subordinate in user_dict["subordinates"]:
                    if user_dict.get('username') not in subordinates.keys():
                        subordinates[user_dict.get('username')] = []
                    subordinates[user_dict.get('username')].append(subordinate)
        session.commit()
        if subordinates:
            for username, user_subordinates in subordinates.items():
                parent_id = session.query(User).filter(User.username == username).first().id
                for subordinate in user_subordinates:
                    child_id = session.query(User).filter(User.username == subordinate).first().id
                    group = UsersGroup(
                        parent_id=parent_id,
                        child_id=child_id,
                        is_active=True
                    )
                    session.add(group)
            session.commit()
        session.close()
    logger.info("Users created")
    return agents_start + 2, agents_end + 2


def load_random_users(size: int = 100) -> int:
    """
    Generates and loads a specified number of random users into the database.
    
    Users are assigned roles based on their index in the generated list.
    
    Parameters:
        size (int): The number of random users to generate. Default is 100.
    
    Returns:
        Tuple[int, int]: A tuple containing the start and end indices of the created users.
    """

    fake = Faker()
    with closing(next(get_session("multiagent"))) as session:
        users_count = session.query(User).count()
        if users_count > 1:
            logger.info("Users already exist")
            return 0, 0
        agent_role = session.query(UserRole).filter(UserRole.code == "AGENT").first()
        supervisor_role = session.query(UserRole).filter(UserRole.code == "SUPERVISOR").first()
        principal_role = session.query(UserRole).filter(UserRole.code == "PRINCIPAL").first()
        agents, supervisors, principals = [], [], []
        for index in range(size):
            selected_role = agent_role
            if index >= int(size * 0.7) and index < int(size * 0.9):
                selected_role = supervisor_role
            elif index >= int(size * 0.9):
                selected_role = principal_role
            # print(selected_role.code)
            user = User(
                username=fake.user_name(),
                full_name=fake.name(),
                email=fake.email(),
                password=pwd_context.hash("password"),
                role=selected_role,
                is_active=True
            )
            if selected_role == agent_role:
                agents.append(user)
            elif selected_role == supervisor_role:
                supervisors.append(user)
            else:
                principals.append(user)
            session.add(user)
        session.flush()
        subs_per_principal = len(supervisors) // len(principals)
        for index, created_principal in enumerate(principals):
            subordinates = supervisors[index * subs_per_principal: (index + 1) * subs_per_principal]
            for subordinate in subordinates:
                group = UsersGroup(parent_id=created_principal.id, child_id=subordinate.id, is_active=True)
                session.add(group)
        subs_per_supervisor = len(agents) // len(supervisors)
        for index, created_supervisor in enumerate(supervisors):
            subordinates = agents[index * subs_per_supervisor: (index + 1) * subs_per_supervisor]
            for subordinate in subordinates:
                group = UsersGroup(parent_id=created_supervisor.id, child_id=subordinate.id, is_active=True)
                session.add(group)
        session.commit()
        count = session.query(User).count()
        session.close()
    logger.info(f"{count} users created")
    return 0, len(agents) - 1

def load_conversations(users_start: int, users_end: int) -> bool|None:
    """
    Creates and loads conversations into the database, assigning them to users.
    
    Each conversation contains a series of messages.
    
    Parameters:
        users_start (int): The starting index of users for conversation assignment.
        users_end (int): The ending index of users for conversation assignment.
    
    Returns:
        bool: True if conversations are created successfully, False otherwise.
    """
    fake = Faker()
    with closing(next(get_session("multiagent"))) as session:
        # Create assigned conversations
        for _ in range(30):
            state_id = fake.random_int(1, 3)
            state = session.query(ConversationState).filter(ConversationState.id == state_id).first()
            user_id = fake.random_int(users_start, users_end) if state.id in [1, 2] else None
            user = session.query(User).filter(User.id == user_id).first()
            phone = fake.phone_number()
            conversation = Conversation(
                conversation_id=f'{phone}-{uuid.uuid4()}',
                client_phone=phone,
                assigned_user_id=user_id,
                credit_number=fake.credit_card_number(),
                state=state,
                last_message=fake.sentence(),
            )
            for i in range(10):
                message = Message(
                    content=fake.sentence(),
                    sender_type=SenderTypeEnum.CLIENT if i % 2 == 0 else SenderTypeEnum.AGENT,
                    conversation=conversation,
                    user_id=user_id if i % 2 != 0 else None,
                )
                session.add(message)
            session.add(conversation)
        session.commit()
        session.close()
    logger.info("Conversations created")
    return True


def load_templates() -> bool:
    """
    Loads templates from a JSON file into the database.
    
    If templates already exist, no more are loaded.
    
    Returns:
        bool: True if templates are created successfully, False otherwise.
    """
    with closing(next(get_session("multiagent"))) as session:
        # Check if templates already exist
        count = session.query(Template).count()
        if count > 0:
            logger.info("Templates already exist")
            return False
        with open(cd + "/templates.json", "r", encoding="utf-8") as file:
            templates = json.load(file)
        for template_dict in templates:
            template = Template(
                content=template_dict.get("content")
            )
            session.add(template)
        session.commit()
        session.close()
    logger.info("Templates created")
    return True


if __name__ == "__main__":
    initialize_database()
    load_default_data()
    users_start, users_end = load_users()
    # if users_end > 0:
    #     load_conversations(users_start, users_end)
    load_templates()
    # load_admin()