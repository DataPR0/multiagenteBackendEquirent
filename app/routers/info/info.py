from fastapi import APIRouter, HTTPException
from app.helpers import users

router = APIRouter()

@router.get("/{entity}/", status_code=200)
async def get_list_by_entity(entity: str) -> list:
    """
    Retrieves a list of entities based on the provided entity type.

    Args:
    entity (str): The type of entity to retrieve (e.g., 'roles').

    Returns:
    list: A list of entities of the specified type.

    Raises:
    HTTPException: If the entity type is not supported.
    """
    if entity == 'states':
        entity_list = users.get_all_user_states()
    elif entity == 'roles':
        entity_list = users.get_all_users_roles()
    else:
        raise HTTPException(status_code=400, detail="Unsupported entity type")
    return entity_list
