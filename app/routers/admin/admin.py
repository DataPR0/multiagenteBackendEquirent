from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, status, Query
from app.helpers import users
from app.models.user import CreateUser, UserRoleEnum, UpdateUserStatus, CreateUsersRelation
from app.utilities.logger import logger
from app.utilities.mailing import send_account_activation_email
from app.routers.auth import auth
from app.config import settings
from datetime import datetime, timedelta
from typing import Optional

import pytz


async def check_if_user_is_admin(request: Request) -> bool:
    """
    Checks if the current user has admin privileges.

    Args:
    request (Request): The incoming request.

    Returns:
    bool: True if the user is an admin, False otherwise.

    Raises:
    HTTPException: If the user is not authenticated or does not have admin privileges.
    """
    privileges_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User does not have enough privileges",
    )
    user = request.state.current_user
    if not user:
        raise privileges_exception
    if user.role_id not in [
        UserRoleEnum.ADMIN.value,
        UserRoleEnum.PRINCIPAL.value,
        UserRoleEnum.SUPERVISOR.value,
        UserRoleEnum.SUPPORT.value,
        UserRoleEnum.DATA_SECURITY.value,
        UserRoleEnum.AUDIT.value
    ]:
        raise privileges_exception
    return True

router = APIRouter()


@router.get("/users", status_code=200)
async def get_users(term: str = "", page: int = 1, limit: int = 10):
    """
    Retrieves a list of users based on the provided filters.

    Args:
    term (str): The search term to filter users by. Defaults to an empty string.
    page (int): The page number for pagination. Defaults to 1.
    limit (int): The number of users to return per page. Defaults to 10.

    Returns:
    list: A list of user data.
    """
    users_data = users.get_users_with_filters(term, page, limit)
    return users_data


@router.get("/logs", status_code=200)
async def get_logs(
        term: str = "", page: int = 1, limit: int = 10,
        start_date: Optional[datetime] = Query(None),
        end_date: Optional[datetime] = Query(None),
        client_timezone: Optional[str] = Query(None)
    ):
    """
    Retrieves a list of logs based on the provided filters.

    Args:
    term (str): The search term to filter logs by. Defaults to an empty string.
    page (int): The page number for pagination. Defaults to 1.
    limit (int): The number of logs to return per page. Defaults to 10.
    start_date (datetime): The start date for filtering logs. Defaults to None.
    end_date (datetime): The end date for filtering logs. Defaults to None.
    client_timezone (str): The client's timezone for date filtering. Defaults to None.

    Returns:
    list: A list of log data.
    """
    if client_timezone:
        try:
            tz = pytz.timezone(client_timezone)
        except pytz.UnknownTimeZoneError:
            raise HTTPException(status_code=400, detail="Invalid timezone")
    else:
        tz = pytz.UTC
    logs_data = users.get_logs_with_filters(
        term, page, limit, start_date, end_date, tz
    )
    return logs_data


@router.post("/users", status_code=200)
async def create_user(tasks: BackgroundTasks, user_payload: CreateUser):
    """
    Creates a new user based on the provided payload.

    Args:
    tasks (BackgroundTasks): The background tasks to run after creating the user.
    user_payload (CreateUser): The payload containing the user's data.

    Returns:
    dict: The created user's data.

    Raises:
    HTTPException: If the username or email is already taken.
    """
    # Validate payload
    if users.get_user_by_username(user_payload.username):
        raise HTTPException(status_code=400, detail="Username is already taken")
    if users.get_user_by_email(user_payload.email):
        raise HTTPException(status_code=400, detail="Email is already taken")
    user = users.create_user(user_payload)
    if not user:
        raise HTTPException(status_code=500, detail="Error while creating user")
    activation_token_expires = timedelta(minutes=settings.jwt_reset_expiration)
    activation_token = auth.create_reset_token(
        data={"sub": user["username"]}, expires_delta=activation_token_expires
    )
    logger.info(f"Activation token: {activation_token}")
    tasks.add_task(send_account_activation_email, user["email"], activation_token)
    return user


@router.patch("/users/{id}/status", status_code=200)
async def change_user_status(id: int, payload: UpdateUserStatus):
    """
    Updates the status of a user.

    Args:
    id (int): The ID of the user to update.
    payload (UpdateUserStatus): The payload containing the new status.

    Returns:
    dict: The updated user's data.

    Raises:
    HTTPException: If the user does not exist or the account has not been configured yet.
    """
    user = users.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")
    if not user.password:
        raise HTTPException(status_code=400, detail="Account has not been configured yet")
    is_active = True if payload.status == "active" else False
    user = users.change_user_status(id, is_active)
    if not user:
        raise HTTPException(status_code=500, detail="Error while changing user status")
    return {
        "id": user.id,
        "status": payload.status,
        "message": "User status updated successfully"
    }


@router.get("/users/{parent_id}/children", status_code=200)
async def get_user_children(parent_id: int):
    """
    Retrieves a list of children for a given parent user.

    Args:
    parent_id (int): The ID of the parent user.

    Returns:
    list: A list of child user data.

    Raises:
    HTTPException: If the parent user does not exist.
    """
    if not users.get_user_by_id(parent_id):
        raise HTTPException(status_code=400, detail="Parent user does not exist")
    children = users.get_user_children(parent_id)
    if not children:
        raise HTTPException(status_code=500, detail="Error while getting user's children")
    return children


@router.post("/users/{parent_id}/children", status_code=200)
async def create_parent_child_relation(parent_id: int, payload: CreateUsersRelation):
    """
    Creates a new parent-child relation between two users.

    Args:
    parent_id (int): The ID of the parent user.
    payload (CreateUsersRelation): The payload containing the child user's ID.

    Returns:
    dict: The created relation data.

    Raises:
    HTTPException: If the parent or child user does not exist.
    """
    if not users.get_user_by_id(parent_id):
        raise HTTPException(status_code=400, detail="Parent user does not exist")
    if not users.get_user_by_id(payload.child_id):
        raise HTTPException(status_code=400, detail="Child user does not exist")
    relation = users.create_users_relation(parent_id, payload.child_id)
    if not relation:
        raise HTTPException(status_code=500, detail="Error while creating relation")
    return relation
