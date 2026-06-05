import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.engine import get_async_session
from app.models.enums import UserRole
from app.models.user import TokenBlocklist, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_password_reset_token(token: str, token_hash: str) -> bool:
    return hash_password_reset_token(token) == token_hash


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    result = await session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    blocklist_result = await session.execute(
        select(TokenBlocklist).where(TokenBlocklist.user_id == user.id)
    )
    if blocklist_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been banned",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been banned",
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted",
        )

    return user


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None

    try:
        payload = decode_access_token(credentials.credentials)
    except HTTPException:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    result = await session.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or user.is_banned or user.is_deleted:
        return None

    blocklist_result = await session.execute(
        select(TokenBlocklist).where(TokenBlocklist.user_id == user.id)
    )
    if blocklist_result.scalar_one_or_none() is not None:
        return None

    return user


def require_role(required_role: UserRole):
    async def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role",
            )
        return current_user

    return dependency


require_freelancer = require_role(UserRole.freelancer)
require_client = require_role(UserRole.client)
require_admin = require_role(UserRole.admin)
