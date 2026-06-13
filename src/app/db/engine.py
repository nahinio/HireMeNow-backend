import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    # pre_ping adds a full round-trip before every checkout; with a remote DB that
    # is expensive. We instead keep connections fresh via keepalive + recycle.
    pool_pre_ping=False,
    pool_size=10,
    max_overflow=20,
    # Recycle connections before serverless providers (e.g. Neon) drop idle ones,
    # so a "warm" request never pays the full reconnect/wake cost.
    pool_recycle=280,
    connect_args={
        "ssl": "require",
        "server_settings": {"application_name": "hiremenow"},
    },
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
