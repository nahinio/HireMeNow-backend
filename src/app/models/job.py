import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Numeric, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.columns import timestamptz
from app.models.db_types import application_status_enum, job_status_enum
from app.models.enums import ApplicationStatus, JobStatus
from app.models.user import utcnow


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    title: str = Field(sa_column=Column(Text, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    deliverables: str = Field(sa_column=Column(Text, nullable=False))
    budget: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    timeline: str = Field(sa_column=Column(Text, nullable=False))
    status: JobStatus = Field(
        default=JobStatus.open,
        sa_column=Column(job_status_enum, nullable=False, server_default="open"),
    )
    posted_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )


class JobRequiredSkill(SQLModel, table=True):
    __tablename__ = "job_required_skills"

    skill_id: uuid.UUID = Field(foreign_key="skills.id", primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", primary_key=True)


class Application(SQLModel, table=True):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("freelancer_id", "job_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    freelancer_id: uuid.UUID = Field(foreign_key="freelancer_profiles.id", nullable=False)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", nullable=False)
    quiz_score_snapshot: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    status: ApplicationStatus = Field(
        default=ApplicationStatus.pending,
        sa_column=Column(
            application_status_enum, nullable=False, server_default="pending"
        ),
    )
    applied_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
