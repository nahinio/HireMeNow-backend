from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import JobStatus
from app.schemas.job import ApplicantListResponse, JobListResponse, JobResponse


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
