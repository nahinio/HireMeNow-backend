import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.core.config import get_settings, neon_connect_args

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    # NullPool avoids stale connections through Neon PgBouncer after deploy/migrations.
    poolclass=NullPool,
    connect_args=neon_connect_args(),
    echo=False,
)


async def warmup_pool() -> None:
    """Open and validate a DB connection at startup.

    This wakes a suspended serverless database and primes the connection pool
    so the first real user request doesn't eat the multi-second cold-start cost.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - best-effort warmup
        logger.warning("DB warmup ping failed", exc_info=True)


async def keepalive_ping() -> None:
    """Lightweight ping to keep the serverless DB awake and the pool warm."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - best-effort keepalive
        logger.debug("DB keepalive ping failed", exc_info=True)


async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
