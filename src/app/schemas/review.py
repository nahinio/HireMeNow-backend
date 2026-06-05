from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import DisputeStatus, JobStatus


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=20)


class ReviewResponse(BaseModel):
    id: UUID
    job_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    rating: int
    body: str
    is_published: bool
    published_at: datetime | None
    submitted_at: datetime

    model_config = {"from_attributes": True}


class DisputeCreate(BaseModel):
    job_id: UUID
    description: str


class DisputeResponse(BaseModel):
    id: UUID
    job_id: UUID
    raised_by: UUID
    resolved_by: UUID | None
    description: str
    status: DisputeStatus
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class DisputeListResponse(BaseModel):
    items: list[DisputeResponse]
    page: int
    limit: int
    total: int


class DisputeResolveRequest(BaseModel):
    resolution_notes: str | None = None
    new_job_status: JobStatus | None = None
    status: DisputeStatus | None = None


class ReviewDeleteResponse(BaseModel):
    review_id: UUID
    reviewee_id: UUID
    avg_rating: Decimal
    review_count: int


class BanRequest(BaseModel):
    ban_reason: str


class BanResponse(BaseModel):
    user_id: UUID
    role: str
    pending_applications_deleted: int = 0
    jobs_closed: int = 0
    applications_canceled: int = 0
