import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.exc import NotSupportedError

from app.core.security import hash_password
from app.db.engine import async_session_maker, engine
from app.models.enums import UserRole
from app.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = "admin@hiremenow.com"
DEFAULT_ADMIN_PASSWORD = "password"


async def _ensure_default_admin_once() -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == DEFAULT_ADMIN_EMAIL)
        )
        if result.scalar_one_or_none() is not None:
            return

        session.add(
            User(
                email=DEFAULT_ADMIN_EMAIL,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role=UserRole.admin,
            )
        )
        await session.commit()


async def ensure_default_admin() -> None:
    """Create the default admin if missing.

    Neon pooler connections can briefly return InvalidCachedStatementError right
    after Alembic migrations in pre-deploy; retry with a fresh connection.
    """
    for attempt in range(4):
        try:
            await _ensure_default_admin_once()
            return
        except NotSupportedError as exc:
            stale_cache = "InvalidCachedStatementError" in str(exc)
            if not stale_cache or attempt == 3:
                raise
            logger.warning(
                "Neon pooler returned stale prepared statement cache on startup "
                "(attempt %s); retrying",
                attempt + 1,
            )
            await engine.dispose()
            await asyncio.sleep(0.75 * (attempt + 1))
