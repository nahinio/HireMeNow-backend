import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args={"ssl": "require"}
    )
    async with engine.connect() as conn:
        enums = await conn.execute(
            text("SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY 1")
        )
        print("Enums:", [row[0] for row in enums.fetchall()])

        tables = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"
            )
        )
        print("Tables:", [row[0] for row in tables.fetchall()])

        try:
            version = await conn.execute(text("SELECT * FROM alembic_version"))
            print("Alembic:", version.fetchall())
        except Exception as exc:
            print("Alembic:", exc)

        columns = await conn.execute(
            text(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name IN ('created_at', 'updated_at')
                """
            )
        )
        print("User timestamps:", columns.fetchall())

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
