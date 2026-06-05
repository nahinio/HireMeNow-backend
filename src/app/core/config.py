from functools import lru_cache
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(value: str) -> str:
    """Convert Neon/psycopg URLs to asyncpg and strip unsupported query params."""
    if value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
    if not value.startswith("postgresql+asyncpg://"):
        raise ValueError("DATABASE_URL must use postgresql:// or postgresql+asyncpg://")

    parsed = urlparse(value)
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key in ("sslmode", "channel_binding"):
        query.pop(key, None)

    clean_query = urlencode(
        {key: values[0] for key, values in query.items() if values},
        doseq=False,
    )
    return urlunparse(parsed._replace(query=clean_query))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "DATABASE_URL is required. Set it in your environment or .env file."
            )
        if "sslmode=require" not in value:
            raise ValueError(
                "DATABASE_URL must include sslmode=require for Neon Postgres."
            )
        return normalize_database_url(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
