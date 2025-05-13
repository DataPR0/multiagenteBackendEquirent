from fastapi import APIRouter, HTTPException, Request
from app.helpers import conversations, users
from app.models.user import UserStateEnum

router = APIRouter()


@router.post("", status_code=200)
async def get_users_by_role(request: Request):
    """
    Retrieves a list of users based on their role.

    Args:
    - request (Request): The incoming request containing the role ID.

    Returns:
    - A list of users matching the specified role.

    Raises:
    - HTTPException: If the role ID is missing from the request body.
    """
    data = await request.json()
    if "role_id" not in data:
        raise HTTPException(status_code=400, detail="Role id is required")
    users_list = users.get_all_users_by_role(data["role_id"], data.get("user_id", None))
    return users_list


@router.post("/{id}")
async def get_users_by_conversation(id: int):
    """
    Retrieves a list of users participating in a conversation.

    Args:
    - id (int): The ID of the conversation.

    Returns:
    - A list of users participating in the specified conversation.

    Raises:
    - HTTPException: If the conversation is not found.
    """
    conversation = conversations.get_conversation_by_id(id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    user_list = users.get_all_users_by_conversation(id)
    return user_list

@router.put("/{id}/state")
async def change_user_state(request: Request, id: str):
    """
    Updates the state of a user.

    Args:
    - request (Request): The incoming request containing the new state ID.
    - id (str): The ID of the user.

    Returns:
    - A dictionary containing the updated user ID, state, and a success message.

    Raises:
    - HTTPException: If the user or state is not found.
    """
    data = await request.json()
    user = users.change_user_state(id, data["state_id"])
    if data["state_id"] == UserStateEnum.ONLINE.value:
        await conversations.massive_asignation()
    if not user:
        raise HTTPException(status_code=404, detail="User not found or state not found")
    return {
        "user_id": user.id,
        "state": user.state_id,
        "message": "User state updated"
    }