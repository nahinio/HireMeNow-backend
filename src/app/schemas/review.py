from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


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
