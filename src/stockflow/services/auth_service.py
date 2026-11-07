"""Authentication and user account management service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.core.config import settings
from stockflow.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from stockflow.core.security import create_access_token, get_password_hash, verify_password
from stockflow.models.user import User, UserRole
from stockflow.schemas.auth import TokenResponse, UserCreate


async def register_user(
    session: AsyncSession,
    payload: UserCreate,
    *,
    internal_role: UserRole = UserRole.CUSTOMER,
) -> User:
    """Register a new user. Role is controlled internally and defaults to CUSTOMER."""
    normalized_email = payload.email.lower().strip()

    existing_stmt = select(User).where(User.email == normalized_email)
    existing_user = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing_user is not None:
        raise ConflictError(
            f"User with email '{normalized_email}' is already registered.",
            details={"email": normalized_email},
        )

    user = User(
        email=normalized_email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=internal_role.value,
        is_active=True,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            f"User with email '{normalized_email}' is already registered.",
            details={"email": normalized_email},
        ) from exc

    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> TokenResponse:
    """Verify credentials and issue a short-lived JWT access token."""
    normalized_email = email.lower().strip()
    stmt = select(User).where(User.email == normalized_email)
    user = (await session.execute(stmt)).scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("User account is inactive.")

    access_token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User:
    """Fetch an active user by UUID primary key."""
    stmt = select(User).where(User.id == user_id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise NotFoundError(f"User '{user_id}' not found.")
    return user
