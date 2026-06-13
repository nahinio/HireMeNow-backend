from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import JobStatus
from app.schemas.job import ApplicantListResponse, JobListResponse, JobResponse


class AdminUserSummary(BaseModel):
    id: UUID
    email: str
    role: str
    display_name: str
    is_banned: bool
    is_deleted: bool
    ban_reason: str | None = None
    created_at: datetime
    deleted_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserSummary]
    page: int
    limit: int
    total: int


class AdminUserDeleteResponse(BaseModel):
    user_id: UUID
    role: str
    deleted_at: datetime

class AdminJobSummary(BaseModel):
    job: JobResponse
    application_count: int
    pending_count: int
    accepted_count: int


class AdminJobListResponse(BaseModel):
    items: list[AdminJobSummary]
    page: int
    limit: int
    total: int


class AdminJobApplicantsResponse(BaseModel):
    job_id: UUID
    applicants: ApplicantListResponse


class AdminStatsResponse(BaseModel):
    pending_reports: int = 0
    total_jobs: int = 0
    open_jobs: int = 0
    filled_jobs: int = 0
    pending_confirmation_jobs: int = 0
    completed_jobs: int = 0
    closed_jobs: int = 0
    total_courses: int = 0
    total_freelancers: int = 0
    total_skills: int = 0
    total_applications: int = 0
    pending_applications: int = 0
