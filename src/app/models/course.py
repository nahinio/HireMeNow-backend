import uuid
from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.models.columns import timestamptz
from app.models.user import utcnow


class Course(SQLModel, table=True):
    __tablename__ = "courses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    skill_id: uuid.UUID = Field(foreign_key="skills.id", nullable=False, index=True)
    name: str = Field(sa_column=Column(Text, nullable=False))
    thumbnail_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    link: str = Field(sa_column=Column(Text, nullable=False))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
