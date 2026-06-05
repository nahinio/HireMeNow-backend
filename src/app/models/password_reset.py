import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.models.columns import timestamptz
from app.models.user import utcnow


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    token_hash: str = Field(sa_column=Column(Text, nullable=False, index=True))
    expires_at: datetime = Field(sa_column=Column(timestamptz, nullable=False))
    used_at: Optional[datetime] = Field(
        default=None, sa_column=Column(timestamptz, nullable=True)
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
