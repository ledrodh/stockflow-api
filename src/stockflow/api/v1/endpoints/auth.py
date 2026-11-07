"""Authentication endpoints (registration, JWT login, and user profile)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from stockflow.api.dependencies import CurrentUserDep, DBSessionDep
from stockflow.models.user import UserRole
from stockflow.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse
from stockflow.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer user account",
)
async def register_endpoint(
    payload: UserCreate,
    session: DBSessionDep,
) -> UserResponse:
    """Register a user. Role assignment is strictly internal and always defaults to customer."""
    user = await register_user(session, payload, internal_role=UserRole.CUSTOMER)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password (JSON) and receive a JWT access token",
)
async def login_endpoint(
    payload: UserLogin,
    session: DBSessionDep,
) -> TokenResponse:
    """Verify credentials and issue a short-lived JWT access token."""
    return await authenticate_user(session, payload.email, payload.password)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 form-compatible login endpoint for OpenAPI interactive docs",
)
async def oauth2_token_endpoint(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DBSessionDep,
) -> TokenResponse:
    """Authenticate using OAuth2PasswordRequestForm (username field carries the email)."""
    return await authenticate_user(session, form_data.username, form_data.password)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user profile",
)
async def get_me_endpoint(current_user: CurrentUserDep) -> UserResponse:
    """Return the profile of the authenticated caller."""
    return UserResponse.model_validate(current_user)
