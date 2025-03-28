from contextlib import closing
from typing import List
from app.utilities.db import get_session
from app.models.user import User, UserRoleEnum as UR, UserLogs, EventTypesEnum
from app.models.conversation import (
    Conversation,
    ConversationState,
    ConversationStateEnum
)
from app.models.message import Message, SenderTypeEnum
from app.models.typification import Typification
from app.helpers.users import (
    get_best_free_agent,
    assign_conversation_to_agent,
    get_user_descendants
)
from app.utilities.logger import logger


def get_all_conversations(user_id: int, user_selected_id: int = None) -> List[Conversation]:
    """
    Retrieves all conversations for a given user.

    Args:
    user_id (int): The ID of the user.
    user_selected_id (int, optional): The ID of the user to filter conversations by. Defaults to None.

    Returns:
    List[Conversation]: A list of conversations for the given user.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            user = session.query(User).filter(User.id == user_id).first()
            user_descendants = get_user_descendants(user_selected_id) if user_selected_id else None
            logger.info(f"User descendants: {user_descendants}")
            if user.role_id in (UR.ADMIN.value, UR.PRINCIPAL.value, UR.SUPERVISOR.value, UR.SUPPORT.value, UR.DATA_SECURITY.value, UR.AUDIT.value):
                registros = session.query(Conversation)
                if user_selected_id:
                    registros = registros.filter(Conversation.assigned_user_id.in_(user_descendants))
                registros = registros.order_by(Conversation.updated_at.desc()).all()
            else:
                registros = session.query(Conversation).filter(
                    Conversation.assigned_user_id == user_id
                ).order_by(
                    Conversation.updated_at.desc()
                ).all()
            return [row.to_dict() for row in registros]
    except Exception as e:
        print("get_all_conversations::::::::", e)
        return None


def get_conversation_by_id(id: int) -> Conversation | None:
    """
    Retrieves a conversation by its ID.

    Args:
    id (str): The ID of the conversation.

    Returns:
    Conversation | None: The conversation with the given ID, or None if not found.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            conversation = session.query(Conversation).filter(Conversation.id == id).first()
            session.close()
            return conversation
    except Exception as e:
        return None


def get_conversation_by_thread_id(id: str) -> Conversation | None:
    """
    Retrieves a conversation by its ID.

    Args:
    id (str): The ID of the conversation.

    Returns:
    Conversation | None: The conversation with the given ID, or None if not found.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            conversation_query = session.query(Conversation).filter(Conversation.conversation_id == id)
            conversation = conversation_query.first()
            session.close()
            return conversation
    except Exception as e:
        print("Error obtaining conversation", e)
        return None


def get_conversation_user_messages_count(thread_id: str) -> int:
    try:
        with closing(next(get_session("multiagent"))) as session:
            conversation = session.query(Conversation).filter(Conversation.conversation_id == thread_id).first()
            if not conversation:
                return 0
            count = session.query(Message).filter(Message.conversation_id == conversation.id, Message.sender_type == SenderTypeEnum.AGENT.value).count()
            session.close()
            return count
    except Exception as e:
        print("Error obtaining conversation messages count", e)
        return 0


def end_conversation(conversation_id: int, data: dict | None = None, user: User | None = None) -> bool:
    """
    Ends a conversation by updating its state and adding a typification.

    Args:
    conversation_id (int): The ID of the conversation to end.
    data (dict): A dictionary containing the motive, comment, and client ID for the typification.
    user (User): The user who is ending the conversation.

    Returns:
    bool: True if the conversation was successfully ended, False otherwise.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            conversation = session.query(Conversation).filter(Conversation.id==conversation_id).first()
            conversation.state_id = ConversationStateEnum.CLOSED.value
            if data:
                typification = Typification(
                    conversation_id=conversation_id,
                    motive=data['motive'],
                    comment=data['comment'],
                    credit_number=conversation.credit_number,
                    client_id=data['client_id']
                )
                session.add(typification)
            if user:
                log = UserLogs(
                    user_id=user.id,
                    event_type=EventTypesEnum.END_CHAT.value,
                    event_details=conversation_id
                )
                session.add(log)
            session.commit()
            session.close()
            return True
    except Exception as e:
        print("end_conversation::::", e)
    return False


def get_longest_wait_time_conversation(all=False) -> None | Conversation | list[Conversation]:
    """
    Retrieves the conversation(s) with the longest wait time.

    Args:
    all (bool, optional): If True, returns all conversations with the longest wait time. Defaults to False.

    Returns:
    None | Conversation | list[Conversation]: The conversation(s) with the longest wait time, or None if no conversations are found.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            conversation = session.query(Conversation).filter(
                Conversation.state_id == ConversationStateEnum.PENDING.value
            ).order_by(Conversation.created_at.desc())
            response = conversation.all() if all else conversation.first()
            session.close()
            return response
    except Exception as e:
        return None


def create_conversation(data: dict) -> Conversation:
    """
    Creates a new conversation.

    Args:
    data (dict): A dictionary containing the conversation data.

    Returns:
    Conversation: The newly created conversation.
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            # Extraemos los datos del diccionario
            conversation_id = data.get("thread_id")
            client_phone = data.get("from_number")
            assigned_user_id = None
            credit_number = "numero_credito_seleccionado"
            unread_count = data.get("mensajes_no_leidos", 1)  # Valor por defecto
            state_id = ConversationStateEnum.PENDING.value  # Debemos asegurarnos de que el estado existe
            last_message = data.get("message", "")
            
            # Obtener el estado de la conversación, si existe
            state = session.query(ConversationState).filter(ConversationState.id == state_id).first()
            if not state:
                raise ValueError(f"El estado con ID {state_id} no existe.")

            # Si no se proporciona un usuario asignado, puede ser None
            assigned_user = None
            if assigned_user_id:
                assigned_user = session.query(User).filter(User.id == assigned_user_id).first()
                if not assigned_user:
                    raise ValueError(f"El usuario con ID {assigned_user_id} no existe.")

            # Crear una nueva instancia de Conversation
            new_conversation = Conversation(
                conversation_id=conversation_id,
                client_phone=client_phone,
                assigned_user_id=assigned_user_id,
                credit_number=credit_number,
                unread_count=unread_count,
                state_id=state.id,  # Aseguramos que el estado sea el que existe en la BD
                last_message=last_message
            )

            # Agregar la nueva conversación a la sesión de base de datos
            session.add(new_conversation)
            session.commit()
            session.refresh(new_conversation)
            session.close()
            return new_conversation.to_dict()
    except Exception as e:
        raise Exception(f"Ocurrió un error al crear la conversación: {str(e)}")


def unable_end_conversation_conditional(assigned_user, session_user) -> bool:
    """
    Checks if a conversation cannot be ended based on the assigned user and session user.

    Args:
    assigned_user (User): The user assigned to the conversation.
    session_user (User): The user currently in the session.

    Returns:
    bool: True if the conversation cannot be ended, False otherwise.
    """
    return (
                not assigned_user and 
                session_user.role_id == UR.AGENT.value
            ) or (
                assigned_user and 
                session_user.id != assigned_user.id and
                session_user.role_id == UR.AGENT.value
            )


async def massive_asignation() -> None:
    """
    Assigns conversations to available agents in a massive assignment process.

    This function retrieves the conversations with the longest wait time and assigns them to the available agents.
    It continues the process until there are no more conversations or available agents.
    """
    pending_conversations = get_longest_wait_time_conversation(all=True)
    available_agents = [{ 
                            "id": row[0].id,        # From Agent obj we obtain Agent id and name
                            "full_name": row[0].full_name,
                            "last_date": row[2],    # Last assigned date
                            "count": row[1],         # Count of assigned conversations
                        } for row in get_best_free_agent(all=True)]

    retries = {}
    while True:
        if len(pending_conversations) == 0:
            break
        if len(available_agents) == 0:
            break
        temp_conversation = pending_conversations.pop(0)
        temp_agent = available_agents.pop(0)
        response = await assign_conversation_to_agent(temp_conversation.id, temp_agent['id'])
        if response.success:
            logger.info( 
                "Asignado chat {} para el usuario {}".format(
                    temp_conversation.id, 
                    temp_agent["id"]
                )
            )
            temp_agent['count'] += 1
            temp_agent['last_date'] = response.assignment['created_at']
            if (temp_agent["count"] < 3):
                available_agents.append(temp_agent)
        else:
            if temp_agent["id"] not in retries:
                retries[temp_agent["id"]] = 1
            else:
                retries[temp_agent["id"]] += 1
            if retries[temp_agent["id"]] < 3:
                pending_conversations = [temp_conversation] + pending_conversations
                available_agents = [temp_agent] + available_agents
            else:
                break


def set_uncount_messages(id: int, count: int) -> None:
    """
    Sets the unread count of a conversation.

    Args:
    id (int): The ID of the conversation.
    count (int): The new unread count.

    Returns:
    None
    """
    try:
        with closing(next(get_session("multiagent"))) as session:
            conversation: None|Conversation = session.query(Conversation).filter(Conversation.id==id).first()
            if (conversation):
                conversation.unread_count = count
            session.commit()
            session.close()
    except Exception as e:
        raise e