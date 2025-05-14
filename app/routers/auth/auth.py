from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings
from app.helpers import conversations
from app.models.user import UserStateEnum, User, UserRoleEnum
from app.utilities.logger import logger
from app.utilities.mailing import send_password_reset_email
from app.helpers.users import (
    get_user_by_username,
    get_user_by_email,
    change_user_state,
    change_user_password,
    activate_user_account
)

# to get a string like this run:
# openssl rand -hex 32


class UserData(BaseModel):
    """
    Represents a user's data.

    Attributes:
    id (int): The user's ID.
    username (str): The user's username.
    full_name (str): The user's full name.
    email (str): The user's email.
    role (int): The user's role.
    """
    id: int
    username: str
    full_name: str
    email: str
    role: int
    role_code: str


class LoginResponse(BaseModel):
    """
    Represents a response to a login request.

    Attributes:
    user (UserData): The user's data.
    """
    user: UserData


class RefreshResponse(BaseModel):
    """
    Represents a response to a refresh token request.

    Attributes:
    success (bool): Whether the refresh was successful.
    message (str): A message describing the result.
    """
    success: bool
    message: str


class ResetResponse(BaseModel):
    """
    Represents a response to a password reset request.

    Attributes:
    success (bool): Whether the reset was successful.
    message (str): A message describing the result.
    """
    success: bool
    message: str


class ForgotUsernameResponse(BaseModel):
    """
    Represents a response to a forgot username request.

    Attributes:
    success (bool): Whether the request was successful.
    message (str): A message describing the result.
    username (Optional[str]): The user's username, if found.
    """
    success: bool
    message: str
    username: Optional[str] = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.

    Args:
    plain_password (str): The plain password to verify.
    hashed_password (str): The hashed password to verify against.

    Returns:
    bool: Whether the plain password matches the hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generates a hashed password from a plain password.

    Args:
    password (str): The plain password to hash.

    Returns:
    str: The hashed password.
    """
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticates a user with a given username and password.

    Args:
    username (str): The username to authenticate.
    password (str): The password to authenticate with.

    Returns:
    User | None: The authenticated user, or None if authentication fails.
    """
    user = get_user_by_username(username)
    print(user)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates an access token with the given data and expiration delta.

    Args:
    data (dict): The data to encode in the token.
    expires_delta (timedelta | None): The expiration delta for the token. Defaults to 15 minutes.

    Returns:
    str: The created access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a refresh token with the given data and expiration delta.

    Args:
    data (dict): The data to encode in the token.
    expires_delta (timedelta | None): The expiration delta for the token. Defaults to 15 minutes.

    Returns:
    str: The created refresh token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_refresh_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_reset_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a reset token with the given data and expiration delta.

    Args:
    data (dict): The data to encode in the token.
    expires_delta (timedelta | None): The expiration delta for the token. Defaults to 15 minutes.

    Returns:
    str: The created reset token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_reset_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


async def get_current_user(request: Request) -> User:
    """
    Retrieves the current user from the request.

    Args:
    request (Request): The request to retrieve the user from.

    Returns:
    User: The current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception
    request.state.current_user = user
    return user


@router.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> LoginResponse:
    """
    Handles a login request.

    Args:
    form_data (OAuth2PasswordRequestForm): The login form data.

    Returns:
    LoginResponse: The response containing the user's data and tokens.

    Raises:
    HTTPException: If the username or password is incorrect.
    HTTPException: If an error occurs while changing the user's state.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active and user.role_id not in [
        UserRoleEnum.ADMIN.value,
        UserRoleEnum.SUPPORT.value,
        UserRoleEnum.DATA_SECURITY.value,
        UserRoleEnum.AUDIT.value
    ]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.jwt_expiration)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(minutes=settings.jwt_refresh_expiration)
    refresh_token = create_refresh_token(
        data={"sub": form_data.username}, expires_delta=refresh_token_expires
    )
    user = change_user_state(user.id, UserStateEnum.ONLINE.value)
    if user.role_id == UserRoleEnum.AGENT.value:
        await conversations.massive_asignation()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing user state to ONLINE"
        )
    response = JSONResponse(LoginResponse(
        user=UserData(
            id=user.id,
            username=form_data.username,
            full_name=user.full_name,
            email=user.email,
            role=user.role_id,
            role_code=user.role.code
        )
    ).model_dump())
    cookie_secure = True if settings.environment == 'production' else False
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite='strict'
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=cookie_secure,
        samesite='strict'
    )
    return response


@router.post("/logout")
async def logout(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Handles a logout request.

    Args:
    current_user (User): The current user.

    Returns:
    JSONResponse: A response indicating that the user has been logged out.
    """
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    user = change_user_state(current_user.id, UserStateEnum.OFFLINE.value)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing user state to OFFLINE"
        )
    logger.info(f"User {current_user.id} logged out")
    return response

@router.post("/refresh")
async def refresh_token(request: Request) -> RefreshResponse:
    """
    Refreshes an access token using a refresh token.

    Args:
    request (Request): The request containing the refresh token.

    Returns:
    RefreshResponse: A response containing the new access token.

    Raises:
    HTTPException: If the refresh token is invalid or missing.
    HTTPException: If the user associated with the refresh token is invalid.
    """
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        payload = jwt.decode(refresh_token, settings.jwt_refresh_secret_key, 
                             algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        user = get_user_by_username(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user"
            )
        if user.username != username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user"
            )
        if not user.is_active and user.role_id != UserRoleEnum.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=settings.jwt_expiration)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        response = JSONResponse(RefreshResponse(
            success=True,
            message="Access token generated successfully"
        ).model_dump())
        cookie_secure = True if settings.environment == 'production' else False
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=cookie_secure,
            samesite='strict'
        )
        return response
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )


@router.post("/reset")
async def reset_password(tasks: BackgroundTasks, email: str = Form(...)) -> ResetResponse:
    """
    Resets a user's password by sending a reset token to their email.

    Args:
    tasks (BackgroundTasks): The tasks to run in the background.
    email (str): The email of the user to reset the password for.

    Returns:
    ResetResponse: A response indicating that the reset token has been sent.

    Raises:
    HTTPException: If the user associated with the email is invalid.
    """
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user"
        )
    reset_token_expires = timedelta(minutes=settings.jwt_reset_expiration)
    reset_token = create_reset_token(
        data={"sub": user.username}, expires_delta=reset_token_expires
    )
    logger.info(f"Reset token: {reset_token}")
    tasks.add_task(send_password_reset_email, email, reset_token)
    return ResetResponse(
        success=True,
        message="Reset token sent"
    )


@router.post("/change-password")
async def change_password(password: str = Form(...), 
                          reset_token: str = Form(...)) -> ResetResponse:
    """
    Changes a user's password using a reset token.

    Args:
    password (str): The new password to set.
    reset_token (str): The reset token to use for authentication.

    Returns:
    ResetResponse: A response indicating that the password has been changed.

    Raises:
    HTTPException: If the reset token is invalid or missing.
    HTTPException: If the user associated with the reset token is invalid.
    HTTPException: If an error occurs while changing the user's password.
    """
    try:
        payload = jwt.decode(reset_token, settings.jwt_reset_secret_key, 
                             algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        user = get_user_by_username(username)
        if user.username != username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user"
            )
        
        hashed_password = get_password_hash(password)
        user = change_user_password(user.id, hashed_password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error changing user password"
            )
        return ResetResponse(
            success=True,
            message="Password changed"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )


@router.post("/forgot-username")
async def get_username(
    email: str = Form(...),
    password: str = Form(...)
) -> ForgotUsernameResponse:
    """
    Retrieves a user's username using their email and password.

    Args:
    email (str): The email of the user to retrieve the username for.
    password (str): The password to use for authentication.

    Returns:
    ForgotUsernameResponse: A response containing the user's username.

    Raises:
    HTTPException: If the user associated with the email is invalid.
    HTTPException: If the email or password is incorrect.
    """
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user"
        )
    user = authenticate_user(user.username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    return ForgotUsernameResponse(
        success=True,
        message="Username retrieved successfully",
        username=user.username
    )


@router.post("/activate-account")
async def activate_account(password: str = Form(...), 
                          activate_token: str = Form(...)) -> ResetResponse:
    try:
        payload = jwt.decode(activate_token, settings.jwt_reset_secret_key, 
                             algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        user = get_user_by_username(username)
        if user.username != username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user"
            )
        
        hashed_password = get_password_hash(password)
        user = change_user_password(user.id, hashed_password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error changing user password"
            )
        user = activate_user_account(user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error activating user account"
            )
        return ResetResponse(
            success=True,
            message="Account activated"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activate token"
        )
