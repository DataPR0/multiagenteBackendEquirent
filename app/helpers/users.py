from app.utilities.db import get_session
from app.models.message import Message
from app.models.user import User, UsersGroup, UserRoleEnum as UserRoles, UserState, UserRole, UserStateEnum, CreateUser, StatusEnum
from app.models.user import UserLogs, EventTypesEnum
from app.models.assignment import Assignment, AssignmentTypeEnum
from app.models.conversation import ConversationStateEnum, Conversation
from app.config import settings
from app.utilities.logger import logger
from app.utilities.socket import socket_manager
from app.models.websockets import Notification, ConversationData, NotificationType
from app.helpers.twilio import assing_agent_message

from contextlib import closing

from sqlalchemy import func, select, or_

from pydantic import BaseModel
from datetime import datetime, tzinfo, time

import math
import pytz

class AssignmentResponse(BaseModel):
    """
    Represents the response of an assignment operation.

    Attributes:
        success (bool): Whether the assignment was successful.
        message (str): A message describing the result of the assignment.
        assignment (dict | None): The assigned conversation, or None if the assignment failed.
    """
    success: bool
    message: str
    assignment: dict | None


def create_user(user_payload: CreateUser) -> dict | None:
    """
    Creates a new user.

    Args:
        user_payload (CreateUser): The payload containing the user's information.

    Returns:
        dict | None: A dictionary containing the created user's information, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = User(**user_payload.model_dump(exclude_none=True, exclude=["parent_id"]))
            session.add(user)
            session.flush()
            if user_payload.parent_id:
                parent = session.query(User).filter(User.id == user_payload.parent_id).first()
                if not parent:
                    session.rollback()
                    return None
                relation = UsersGroup(
                    parent_id=user_payload.parent_id,
                    child_id=user.id,
                    is_active=True
                )
                session.add(relation)
            session.commit()
            response = {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role_id": user.role_id
            }
            session.close()
            return response
    except Exception as e:
        logger.error(f"Error while creating user: {e}")
    return None


def change_user_status(user_id: int, is_active: bool) -> User | None:
    """
    Changes the status of a user.

    Args:
        user_id (int): The ID of the user to change the status for.
        is_active (bool): The new status of the user.

    Returns:
        User | None: The updated user, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                return None
            user.is_active = is_active
            session.commit()
            session.refresh(user)
            session.close()
            return user
    except Exception as e:
        print(f"Error changing user status ({user_id}): {e}")
    return None


def get_users_with_filters(term: str = "", page: int = 1, limit: int = 10) -> dict | None:
    """
    Retrieves a list of users with filters.

    Args:
        term (str, optional): The search term to filter users by. Defaults to "".
        page (int, optional): The page number to retrieve. Defaults to 1.
        limit (int, optional): The number of users to retrieve per page. Defaults to 10.

    Returns:
        dict | None: A dictionary containing the filtered users, or None if an error occurs.
    """
    try:
        offset = (page - 1) * limit
        with closing(next(get_session('multiagent'))) as session:
            users_query = select(User)
            if term:
                users_query = users_query.filter(or_(
                    User.username.like(f"%{term}%"),
                    User.email.like(f"%{term}%"),
                    User.full_name.like(f"%{term}%")
                ))
            count = session.execute(users_query.with_only_columns(func.count(User.id))).scalar_one()
            users_query = users_query.order_by(User.id).offset(offset).limit(limit)
            users = session.execute(users_query).scalars().all()
            response = {
                "data": [{
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "email": user.email,
                    "role_id": user.role_id,
                    "role": user.role.code,
                    "state": user.state.code if user.state else None,
                    "status": StatusEnum.ACTIVE if user.is_active else StatusEnum.INACTIVE,
                    "children_count": len(user.associations_as_parent)
                } for user in users],
                "total": count,
                "per_page": limit,
                "current_page": page,
                "last_page": math.ceil(count / limit),
                "from": offset + 1,
                "to": min(offset + limit, count)
            }
            session.close()
            return response
    except Exception as e:
        logger.error(f"Error getting users with filters: {e}")
    return None


def get_logs_with_filters(
        term: str = "", page: int = 1, limit: int = 10,
        start_date: datetime = None, end_date: datetime = None,
        tz: tzinfo = None
    ) -> dict | None:
    """
    Retrieves logs with filters.

    Args:
        term (str, optional): The search term to filter logs by. Defaults to "".
        page (int, optional): The page number to retrieve. Defaults to 1.
        limit (int, optional): The number of logs to retrieve per page. Defaults to 10.
        start_date (datetime, optional): The start date to filter logs by. Defaults to None.
        end_date (datetime, optional): The end date to filter logs by. Defaults to None.
        tz (tzinfo, optional): The timezone to use for date filtering. Defaults to None.

    Returns:
        dict | None: A dictionary containing the filtered logs, or None if an error occurs.
    """
    try:
        offset = (page - 1) * limit
        with closing(next(get_session('multiagent'))) as session:
            logs_query = select(UserLogs).join(User, UserLogs.user_id == User.id)
            if term:
                logs_query = logs_query.filter(or_(
                    User.full_name.like(f"%{term}%"),
                    User.username.like(f"%{term}%"),
                    User.email.like(f"%{term}%"),
                    UserLogs.event_details.like(f"%{term}%")
                ))
            if start_date:
                # Start of the day in the client's timezone
                start_date_dt = datetime.combine(start_date, time.min).replace(tzinfo=tz)
                # Convert to UTC
                start_date_utc = start_date_dt.astimezone(pytz.UTC)
                logs_query = logs_query.filter(
                    UserLogs.created_at >= start_date_utc
                )
            if end_date:
                # End of the day in the client's timezone
                end_date_dt = datetime.combine(end_date, time.max).replace(tzinfo=tz)
                # Convert to UTC
                end_date_utc = end_date_dt.astimezone(pytz.UTC)
                logs_query = logs_query.filter(
                    UserLogs.created_at <= end_date_utc
                )
            count = session.execute(logs_query.with_only_columns(func.count(UserLogs.id))).scalar_one()
            logs_query = logs_query.order_by(-UserLogs.id).offset(offset).limit(limit)
            logs = session.execute(logs_query).scalars().all()
            response = {
                "data": [{
                    "id": log.id,
                    "user_id": log.user_id,
                    "user": {
                        "id": log.user.id,
                        "username": log.user.username,
                        "full_name": log.user.full_name,
                        "email": log.user.email,
                        "role_id": log.user.role_id,
                        "role": log.user.role.code
                    },
                    "event_type_id": log.event_type,
                    "event_type": log.type,
                    "event_details": log.event_details,
                    "created_at": log.created_at.replace(tzinfo=pytz.UTC).isoformat()
                } for log in logs],
                "total": count,
                "per_page": limit,
                "current_page": page,
                "last_page": math.ceil(count / limit),
                "from": offset + 1,
                "to": min(offset + limit, count)
            }
            session.close()
            return response
    except Exception as e:
        logger.error(f"Error getting logs with filters: {e}")
    return None


def get_user_children(parent_id: int) -> list[dict] | None:
    """
    Retrieves the children of a user.

    Args:
        parent_id (int): The ID of the parent user.

    Returns:
        list[dict] | None: A list of dictionaries containing the children's information, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == parent_id).first()
            if user is None:
                return None
            user_relations = session.query(UsersGroup).filter(UsersGroup.parent_id == parent_id).all()
            response = [{
                "parent_id": assoc.parent_id,
                "child_id": assoc.child_id,
                "child": {
                    "username": assoc.child.username,
                    "full_name": assoc.child.full_name,
                    "email": assoc.child.email,
                    "role_id": assoc.child.role_id,
                    "role": assoc.child.role.code,
                    "status": StatusEnum.ACTIVE if assoc.child.is_active else StatusEnum.INACTIVE,
                    "children_count": len(assoc.child.associations_as_parent)
                },
                "is_active": assoc.is_active,
                "created_at": assoc.created_at,
                "updated_at": assoc.updated_at
            } for assoc in user_relations]
            session.close()
            return response
    except Exception as e:
        print(f"Error while getting user's children ({parent_id}): {e}")
    return None


def create_users_relation(parent_id: int, child_id: int) -> dict | None:
    """
    Creates a relation between two users.

    Args:
        parent_id (int): The ID of the parent user.
        child_id (int): The ID of the child user.

    Returns:
        dict | None: A dictionary containing the created relation's information, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            parent = session.query(User).filter(User.id == parent_id).first()
            if not parent:
                return None
            child = session.query(User).filter(User.id == child_id).first()
            if not child:
                return None
            # Check if child already has a parent
            child_parent_relation = session.query(UsersGroup).filter(
                UsersGroup.child_id == child_id
            ).first()
            if child_parent_relation:
                session.close()
                logger.error(f"Cannot create relation between {parent_id} and {child_id}. User {child_id} is subordinate of {child_parent_relation.parent_id}")
                return None
            users_group = UsersGroup(
                parent_id=parent.id,
                child_id=child.id,
                is_active=True
            )
            session.add(users_group)
            session.flush()
            session.commit()
            session.close()
            return {
                "parent_id": users_group.parent_id,
                "child_id": users_group.child_id,
                "is_active": users_group.is_active
            }
    except Exception as e:
        logger.error(f"Error creating users group: {e}")
    return None


def get_user_by_id(user_id: int) -> User | None:
    """
    Retrieves a user by their ID.

    Args:
        user_id (int): The ID of the user to retrieve.

    Returns:
        User | None: The user with the specified ID, or None if not found.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            session.close()
            return user
    except Exception as e:
        print(f"Error getting user: {e}")
    return None


def get_user_by_username(username: str) -> User | None:
    """
    Retrieves a user by their username.

    Args:
        username (str): The username of the user to retrieve.

    Returns:
        User | None: The user with the specified username, or None if not found.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.username == username).first()
            session.close()
            return user
    except Exception as e:
        print(f"Error getting user: {e}")
    return None


def get_user_by_email(email: str) -> User | None:
    """
    Retrieves a user by their email.

    Args:
        email (str): The email of the user to retrieve.

    Returns:
        User | None: The user with the specified email, or None if not found.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.email == email).first()
            session.close()
            return user
    except Exception as e:
        print(f"Error getting user: {e}")
    return None


def get_user_ancestors(user_id: int) -> list[int] | None:
    """
    Retrieves a list of user IDs representing the ancestors of a given user.

    Args:
        user_id (int): The ID of the user for whom to retrieve ancestors.

    Returns:
        list[int] | None: A list of user IDs representing the ancestors of the given user, or None if the user is not found.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                session.close()
                return None
            ancestors = []
            while user.associations_as_child:
                user = user.associations_as_child[0].parent
                ancestors.append(user.id)
            session.close()
            return ancestors
    except Exception as e:
        print(f"Error getting user ancestors: {e}")
    return None


def get_user_descendants(user_id: int) -> list[int] | None:
    """
    Retrieves a list of user IDs representing the descendants of a given user.

    Args:
        user_id (int): The ID of the user for whom to retrieve descendants.

    Returns:
        list[int] | None: A list of user IDs representing the descendants of the given user, or None if the user is not found.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                session.close()
                return None
            if user.role_id == UserRoles.ADMIN.value:
                descendants = [u.id for u in session.query(User).filter(User.role_id == UserRoles.AGENT.value).all()]
                session.close()
                return descendants
            descendants = []
            queue = [user]
            while queue:
                current = queue.pop(0)
                if not current.associations_as_parent:
                    descendants.append(current.id)
                    continue
                for association in current.associations_as_parent:
                    if not association.is_active:
                        continue
                    queue.append(association.child)
            session.close()
            return descendants
    except Exception as e:
        print(f"Error getting user descendants: {e}")
    return None


def get_all_user_states() -> list[dict] | None:
    """
    Retrieves a list of all user states.

    Returns:
        list[UserState] | None: A list of all user states, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user_states = session.query(UserState).all()
            session.close()
            return [state.to_dict() for state in user_states]
    except Exception as e:
        logger.error(f"Error getting user states: {e}")
    return None


def get_all_users_roles() -> list[dict] | None:
    """
    Retrieves a list of all user roles.

    Returns:
        list[UserRole] | None: A list of all user roles, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user_roles = session.query(UserRole).all()
            session.close()
            return [role.to_dict() for role in user_roles]
    except Exception as e:
        logger.error(f"Error while getting users roles: {e}")
    return None


def activate_user_account(user_id):
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                return None
            user.is_active = True
            session.commit()
            session.refresh(user)
            session.close()
            return user
    except Exception as e:
        print(f"Error activating user account ({user_id}): {e}")
    return None


def change_user_state(user_id: int, state_id: int) -> User | None:
    """
    Changes the state of a user.

    Args:
        user_id (int): The ID of the user to change the state for.
        state_id (int): The ID of the new state.

    Returns:
        User | None: The updated user, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                return None
            state = session.query(UserState).filter(UserState.id == state_id).first()
            if state is None:
                return None
            user.state = state
            log = UserLogs(
                user_id=user.id,
                event_type=EventTypesEnum.STATE_CHANGE.value,
                event_details=state.code
            )
            session.add(log)
            session.commit()
            session.refresh(user)
            session.close()
            return user
    except Exception as e:
        logger.error(f"Error changing user state ({user_id}): {e}")
    return None


def change_user_password(user_id: int, hashed_password: str) -> User | None:
    """
    Changes the password of a user.

    Args:
        user_id (int): The ID of the user to change the password for.
        hashed_password (str): The new hashed password.

    Returns:
        User | None: The updated user, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                return None
            user.password = hashed_password
            session.commit()
            session.refresh(user)
            session.close()
            return user
    except Exception as e:
        logger.error(f"Error changing user password ({user_id}): {e}")
    return None


def get_all_users_by_role(role_id: int, user_id: int = None) -> list[dict]:
    """
    Retrieves a list of users with the specified role ID.

    Args:
        role_id (int): The ID of the role to filter users by.
        user_id (int, optional): The ID of the user to filter users by. Defaults to None.

    Returns:
        list[dict] | None: A list of dictionaries containing user information, or None if an error occurs.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            users_query = select(User).filter(User.role_id == role_id).order_by(User.id)
            if user_id:
                logger.info(f"User ID: {user_id}")
                users_query = select(User).join(UsersGroup, UsersGroup.child_id == User.id).filter(
                    User.role_id == role_id, UsersGroup.parent_id == user_id, UsersGroup.is_active
                ).order_by(User.id)
            users = session.execute(users_query).scalars().all()
            response = [{
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role_id": user.role_id,
                "role": user.role.code,
                "status": StatusEnum.ACTIVE if user.is_active else StatusEnum.INACTIVE,
                "children_count": len(user.associations_as_parent)
            } for user in users]
            session.close()
            return response
    except Exception as e:
        logger.error(f"Error getting users by role: {e}")
    return None


def get_all_users_by_conversation(id: int) -> list[User] | None:
    """
    Retrieves a list of users participating in the conversation with the specified ID.

    Args:
        id (str): The ID of the conversation to retrieve users from.

    Returns:
        list[User] | None: A list of users participating in the conversation, or None if an error occurs.
    """
    try:
        with get_session('multiagent') as session:
            messages = session.query(Message).filter_by(conversation_id=id)
            users = [msg.user for msg in messages]
            session.close()
            return users
    except Exception as e:
        print(f"Error saving message: {e}")
    return None


def get_best_free_agent(all=False) -> User | list[User] | None:
    """
    Retrieves the best free agent(s) based on active assignments.

    Args:
        all (bool): If True, returns all available free agents. Otherwise, returns only the best free agent.

    Returns:
        User | list[User] | None: The best free agent(s) or [] / None if no free agents are available.
    """
    try:
        free_agents = None
        # Get best free agent based on active assignments
        with closing(next(get_session('multiagent'))) as session:
            free_agent_query = select(
                User,
                func.max(Assignment.created_at).label('max_assignment_created_at')
            ).join(
                Conversation,
                (Conversation.assigned_user_id == User.id) & 
                (Conversation.state_id == ConversationStateEnum.OPEN.value),
                isouter=True
            ).join(
                Assignment,
                (Assignment.user_id == User.id) & (Assignment.conversation_id == Conversation.id),
                isouter=True
            ).filter(
                User.role_id == UserRoles.AGENT.value,
                User.state_id == UserStateEnum.ONLINE.value
            ).group_by(
                User,
                Conversation.id
            ).order_by(User.id)
            results = session.execute(free_agent_query).all() 
            agents = {}
            session.close()
            for user, max_created_at in results:
                if str(user.id) not in agents:
                    agents[str(user.id)] = [
                        user,
                        1 if max_created_at else 0,
                        max_created_at
                    ]
                else: 
                    agents[str(user.id)][1] += 1
            if (len(agents.keys())):
                free_agents = [agent for agent in agents.values() if agent[1] < settings.max_assignments_per_agent]
                free_agents.sort(key=lambda x: (-x[1], x[2]))
                if not all:
                    free_agents = free_agents[:1]
            elif all:
                free_agents = []
            else:
                free_agents = None
    except KeyError as e:
        print(f"Error getting best free agent: {e}")
    return free_agents[::-1]

async def assign_conversation_to_free_agent(conversation_id: int) -> AssignmentResponse:
    """
    Assigns a conversation to the best available free agent.

    Args:
        conversation_id (int): The ID of the conversation to assign.

    Returns:
        AssignmentResponse: The result of the assignment operation.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            # Check if the conversation has an active assignment
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation.state_id != ConversationStateEnum.PENDING.value:
                return AssignmentResponse(
                    success=False,
                    message="Conversation already " +
                    ( "assigned" if conversation.state_id == ConversationStateEnum.OPEN.value 
                    else "closed"),
                    assignment=None
                )
            if conversation.assigned_user_id is not None:
                return AssignmentResponse(
                    success=False,
                    message="Conversation already assigned",
                    assignment=None
                )
            free_agent, date_update, count = get_best_free_agent()
            logger.info(f"Free agent: {free_agent}")
            if free_agent is None:
                return AssignmentResponse(
                    success=False,
                    message="No free agents available",
                    assignment=None
                )
            session.close()
        response = await assign_conversation_to_agent(conversation_id, free_agent.id)
        return response
    except Exception as e:
        print(f"Error assigning conversation to free agent: {e}")
    return AssignmentResponse(
        success=False,
        message="Error assigning conversation",
        assignment=None
    )


async def assign_conversation_to_agent(conversation_id: int, agent_id: int, current_user: User=None, event_type: int = 1) -> AssignmentResponse:
    """
    Assigns a conversation to a specific agent.

    Args:
        conversation_id (int): The ID of the conversation to assign.
        agent_id (int): The ID of the agent to assign the conversation to.
        current_user (User, optional): The user currently handling the conversation. Defaults to None.
        event_type (int, optional): The type of assignment event. Defaults to 1.

    Returns:
        AssignmentResponse: The result of the assignment operation.

    Raises:
        Exception: If an error occurs during the assignment process.
    """
    try:
        with closing(next(get_session('multiagent'))) as session:
            # Check if the conversation has an active assignment
            conversation: Conversation | None = session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            previous_agent_assigned = conversation.assigned_user_id
            if conversation.assigned_user_id == agent_id and event_type == AssignmentTypeEnum.ASSIGNED.value:
                return AssignmentResponse(
                    success=False,
                    message="Conversation already assigned to agent",
                    assignment=None
                )
            if conversation.assigned_user_id not in [agent_id, None] and event_type == AssignmentTypeEnum.ASSIGNED.value:
                return AssignmentResponse(
                    success=False,
                    message="Conversation already assigned",
                    assignment=None
                )
            if current_user and current_user.id != conversation.assigned_user_id and event_type == AssignmentTypeEnum.TRANSFERRED.value:
                if current_user.role_id not in [UserRoles.PRINCIPAL.value, UserRoles.SUPERVISOR.value]:
                    return AssignmentResponse(
                        success=False,
                        message="Cannot transfer conversation as agent if its not assigned to you",
                        assignment=None
                    )
            # Get the agent
            agent:User|None = session.query(User).filter(User.id == agent_id).first()
            if agent is None:
                session.close()
                return AssignmentResponse(
                    success=False,
                    message="Agent not found",
                    assignment=None
                )
            # Check if agent has less than <max_assignments_per_agent> active assignments
            active_assignments = session.query(Conversation).filter(
                Conversation.assigned_user_id == agent_id,
                Conversation.state_id == ConversationStateEnum.OPEN.value
            ).count()
            if active_assignments >= settings.max_assignments_per_agent and event_type == AssignmentTypeEnum.ASSIGNED.value:
                return AssignmentResponse(
                    success=False,
                    message="Agent has too many assignments",
                    assignment=None
                )
            # Update conversation assigned user
            if event_type != AssignmentTypeEnum.INTERVENTION.value:
                conversation.assigned_user_id = agent_id
            # Update conversation state if needed
            if conversation.state_id == ConversationStateEnum.PENDING.value:
                conversation.state_id = ConversationStateEnum.OPEN.value
            
            # Create assignment
            assignment = Assignment(
                user_id=agent_id,
                conversation_id=conversation_id,
                event_id=event_type
            )
            
            session.add(assignment)
            session.commit()
            conversation_data = ConversationData(
                id=conversation_id,
                client_phone=conversation.client_phone,
                last_message=conversation.last_message,
                unread_count=conversation.unread_count,
                updated_at=conversation.updated_at,
                user_id=agent_id,
                previous_user=previous_agent_assigned,
                state_id=conversation.state_id
            )

            users_to_notify = get_user_ancestors(agent_id)
            admin_users = get_all_users_by_role(role_id=UserRoles.PRINCIPAL.value)
            if users_to_notify:
                users_to_notify = users_to_notify + [user['id'] for user in admin_users if user['id'] not in users_to_notify]
            else:
                users_to_notify = [user['id'] for user in admin_users]
            
            if agent_id and agent_id not in users_to_notify:
                users_to_notify.append(agent_id)
            
            if agent_id != previous_agent_assigned and previous_agent_assigned:
                users_to_notify.append(previous_agent_assigned)
            
            for ancestor_id in users_to_notify:
                # Notify assignment to agent, supervisor and administrators
                await socket_manager.send_notification(ancestor_id, Notification(
                    type=NotificationType.NEW_CONVERSATION if event_type == AssignmentTypeEnum.ASSIGNED.value else NotificationType.NEW_TRANSFER,
                    conversation=conversation_data
                ))
            if event_type == AssignmentTypeEnum.TRANSFERRED.value:
                log = UserLogs(
                    user_id=agent_id,
                    event_type=EventTypesEnum.TRANSFER.value,
                    event_details=conversation_id
                )
                session.add(log)
                session.commit()
            if previous_agent_assigned is None:
                await assing_agent_message(conversation.client_phone, agent.full_name)
            response = AssignmentResponse(
                success=True,
                message="Conversation assigned successfully",
                assignment={
                    "user_id": assignment.user_id,
                    "conversation_id": assignment.conversation_id,
                    "event_id": assignment.event_id,
                    "created_at": assignment.created_at,
                    "updated_at": assignment.updated_at
                }
            )
            session.close()
            return response
    except Exception as e:
        print(f"Error assigning conversation to agent: {e}")
    return AssignmentResponse(
        success=False,
        message="Error assigning conversation",
        assignment=None
    )
