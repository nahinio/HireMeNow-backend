import uuid
from datetime import datetime

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.columns import timestamptz
from app.models.db_types import conversation_phase_enum
from app.models.enums import ConversationPhase
from app.models.user import utcnow


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("job_id", "freelancer_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    freelancer_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", nullable=False)
    phase: ConversationPhase = Field(
        default=ConversationPhase.active,
        sa_column=Column(
            conversation_phase_enum, nullable=False, server_default="active"
        ),
    )
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", nullable=False)
    sender_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    body: str = Field(sa_column=Column(Text, nullable=False))
    is_read: bool = Field(default=False)
    sent_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )


class CompletionSignal(SQLModel, table=True):
    __tablename__ = "completion_signals"
    __table_args__ = (UniqueConstraint("job_id", "signalled_by"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", nullable=False)
    signalled_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    signalled_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
