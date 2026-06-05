from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ReportStatus
from app.schemas.skill import SkillResponse


class UserReportCreate(BaseModel):
    reported_user_id: UUID
    description: str = Field(min_length=1)


class UserReportResolveRequest(BaseModel):
    status: Literal[ReportStatus.approved, ReportStatus.rejected]


class UserReportResponse(BaseModel):
    id: UUID
    reporter_id: UUID
    reported_user_id: UUID
    description: str
    status: ReportStatus
    resolved_by: UUID | None
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class UserReportResolveResponse(BaseModel):
    report: UserReportResponse
    reported_user_deleted_at: datetime | None = None


class UserReportListResponse(BaseModel):
    items: list[UserReportResponse]
    page: int
    limit: int
    total: int


class FreelancerPublicResponse(BaseModel):
    profile_id: UUID
    user_id: UUID
    display_name: str
    bio: str
    profile_picture_url: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    avg_rating: Decimal
    review_count: int
    availability_status: str
    skills: list[SkillResponse] = Field(default_factory=list)


class FreelancerPublicListResponse(BaseModel):
    items: list[FreelancerPublicResponse]
    page: int
    limit: int
    total: int
