from sqlalchemy import select

from app.core.security import hash_password
from app.db.engine import async_session_maker
from app.models.enums import UserRole
from app.models.user import User

DEFAULT_ADMIN_EMAIL = "admin@hiremenow.com"
DEFAULT_ADMIN_PASSWORD = "password"


async def ensure_default_admin() -> None:
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
