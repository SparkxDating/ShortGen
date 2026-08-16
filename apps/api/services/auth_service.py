from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.auth.jwt import create_access_token
from apps.api.auth.passwords import hash_password, verify_password
from apps.api.config import get_settings
from apps.api.models.user import User
from apps.api.schemas.auth import TokenResponse
from apps.api.schemas.user import UserResponse
from apps.api.services import workspace_service
from apps.api.services.errors import ConflictError, UnauthorizedError


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower().strip()))


def register_user(db: Session, email: str, password: str, name: str) -> TokenResponse:
    normalized = email.lower().strip()
    if get_user_by_email(db, normalized):
        raise ConflictError("an account with this email already exists")
    user = User(email=normalized, name=name.strip(), password_hash=hash_password(password))
    db.add(user)
    db.flush()
    workspace_service.create_workspace(db, owner=user, name=f"{user.name}'s workspace")
    db.commit()
    db.refresh(user)
    return issue_token(user)


def authenticate_user(db: Session, email: str, password: str) -> TokenResponse:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("invalid email or password")
    return issue_token(user)


def issue_token(user: User) -> TokenResponse:
    settings = get_settings()
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )
