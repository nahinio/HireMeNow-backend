import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.models.columns import timestamptz
from app.models.user import utcnow


class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", nullable=False)
    reviewer_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    reviewee_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    rating: int = Field(nullable=False)
    body: str = Field(sa_column=Column(Text, nullable=False))
    is_published: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    submitted_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
    published_at: Optional[datetime] = Field(
        default=None, sa_column=Column(timestamptz, nullable=True)
    )


class ReviewReminder(SQLModel, table=True):
    __tablename__ = "review_reminders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", nullable=False)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    reminder_type: str = Field(sa_column=Column(Text, nullable=False))
    sent_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
