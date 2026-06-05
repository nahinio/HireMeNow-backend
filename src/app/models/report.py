import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.models.columns import timestamptz
from app.models.db_types import report_status_enum
from app.models.enums import ReportStatus
from app.models.user import utcnow


class UserReport(SQLModel, table=True):
    __tablename__ = "user_reports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reporter_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    reported_user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    description: str = Field(sa_column=Column(Text, nullable=False))
    status: ReportStatus = Field(
        default=ReportStatus.pending,
        sa_column=Column(report_status_enum, nullable=False, server_default="pending"),
    )
    resolved_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
    resolved_at: Optional[datetime] = Field(
        default=None, sa_column=Column(timestamptz, nullable=True)
    )
