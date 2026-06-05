import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric, Text

from app.models.columns import timestamptz
from sqlmodel import Field, SQLModel

from app.models.db_types import user_role_enum
from app.models.enums import UserRole


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(sa_column=Column(Text, unique=True, index=True, nullable=False))
    password_hash: str = Field(sa_column=Column(Text, nullable=False))
    role: UserRole = Field(sa_column=Column(user_role_enum, nullable=False))
    is_banned: bool = Field(default=False)
    ban_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )


class FreelancerProfile(SQLModel, table=True):
    __tablename__ = "freelancer_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, nullable=False)
    display_name: str = Field(sa_column=Column(Text, nullable=False))
    bio: str = Field(default="", sa_column=Column(Text, nullable=False, server_default=""))
    available_for_work: bool = Field(default=True)
    avg_rating: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric, nullable=False, server_default="0"),
    )
    review_count: int = Field(default=0)
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )


class ClientProfile(SQLModel, table=True):
    __tablename__ = "client_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, nullable=False)
    company_name: str = Field(sa_column=Column(Text, nullable=False))
    avg_rating: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric, nullable=False, server_default="0"),
    )
    review_count: int = Field(default=0)
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )


class PortfolioLink(SQLModel, table=True):
    __tablename__ = "portfolio_links"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    profile_id: uuid.UUID = Field(foreign_key="freelancer_profiles.id", nullable=False)
    label: str = Field(sa_column=Column(Text, nullable=False))
    url: str = Field(sa_column=Column(Text, nullable=False))
    position: int = Field(nullable=False)


class TokenBlocklist(SQLModel, table=True):
    __tablename__ = "token_blocklist"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, nullable=False)
    blocked_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
