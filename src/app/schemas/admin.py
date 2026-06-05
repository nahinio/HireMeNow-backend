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
