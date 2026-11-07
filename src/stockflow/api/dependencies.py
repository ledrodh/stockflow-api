"""FastAPI dependencies for authentication, RBAC authorization, and database sessions."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.core.config import settings
from stockflow.core.exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
)
from stockflow.core.security import decode_access_token
from stockflow.db.session import get_db_session
from stockflow.models.user import User, UserRole
from stockflow.services.auth_service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token",
    auto_error=False,
)

DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    session: DBSessionDep,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    """Resolve and validate the currently authenticated user from the Bearer JWT."""
    if not token:
        raise AuthenticationError("Authentication credentials were not provided.")

    payload = decode_access_token(token)
    try:
        user_id = UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise AuthenticationError("Invalid user identifier in token.") from exc

    try:
        user = await get_user_by_id(session, user_id)
    except NotFoundError as exc:
        raise AuthenticationError("Authenticated user no longer exists.") from exc

    if not user.is_active:
        raise AuthenticationError("User account is inactive.")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_optional_current_user(
    session: DBSessionDep,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User | None:
    """Resolve authenticated user if Bearer token is valid and present, otherwise return None.

    Database operational errors are never swallowed as missing authentication.
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
    except (AuthenticationError, ValueError, KeyError):
        return None

    try:
        user = await get_user_by_id(session, user_id)
        return user if user.is_active else None
    except NotFoundError:
        return None


OptionalCurrentUserDep = Annotated[User | None, Depends(get_optional_current_user)]


async def require_admin(current_user: CurrentUserDep) -> User:
    """Enforce Role-Based Access Control (RBAC): require ADMIN role."""
    if current_user.role != UserRole.ADMIN.value:
        raise PermissionDeniedError("Administrator privileges are required to perform this action.")
    return current_user


AdminUserDep = Annotated[User, Depends(require_admin)]
