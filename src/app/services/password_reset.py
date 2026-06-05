from datetime import datetime, timedelta, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    generate_password_reset_token,
    hash_password,
    hash_password_reset_token,
    verify_password_reset_token,
)
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)

GENERIC_RESET_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)


async def request_password_reset(
    session: AsyncSession, email: str
) -> tuple[str, str | None]:
    settings = get_settings()
    result = await session.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    reset_token: str | None = None
    if user is not None and not user.is_deleted and not user.is_banned:
        raw_token = generate_password_reset_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

        await session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )

        session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_password_reset_token(raw_token),
                expires_at=expires_at,
            )
        )

        if settings.email_is_configured():
            try:
                await send_password_reset_email(user.email, raw_token)
            except Exception:
                logger.exception(
                    "Failed to send password reset email for user_id=%s", user.id
                )
        elif settings.EXPOSE_PASSWORD_RESET_TOKEN:
            reset_token = raw_token
        else:
            logger.warning(
                "Password reset requested but email is not configured "
                "(set SMTP_* and FRONTEND_RESET_URL, or EXPOSE_PASSWORD_RESET_TOKEN=true for dev)"
            )

    return GENERIC_RESET_MESSAGE, reset_token


async def reset_password_with_token(
    session: AsyncSession, token: str, new_password: str
) -> None:
    token_hash = hash_password_reset_token(token)
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(PasswordResetToken, User)
        .join(User, PasswordResetToken.user_id == User.id)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    row = result.one_or_none()
    if row is None or not verify_password_reset_token(token, token_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    reset_record, user = row
    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been banned",
        )

    user.password_hash = hash_password(new_password)
    user.updated_at = now
    reset_record.used_at = now
    session.add(user)
    session.add(reset_record)
