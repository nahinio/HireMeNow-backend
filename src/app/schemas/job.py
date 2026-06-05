from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ApplicationStatus, JobStatus
from app.schemas.skill import SkillResponse
from app.utils.availability import serialize_availability


class JobCreate(BaseModel):
    title: str
    description: str
    deliverables: str
    budget: Decimal
    timeline: str
    required_skill_ids: list[UUID] = Field(min_length=1)


class JobResponse(BaseModel):
    id: UUID
    client_id: UUID
    title: str
    description: str
    deliverables: str
    budget: Decimal
    timeline: str
    status: JobStatus
    posted_at: datetime
    updated_at: datetime
    required_skills: list[SkillResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    page: int
    limit: int
    total: int


class ApplicationResponse(BaseModel):
    id: UUID
    freelancer_id: UUID
    job_id: UUID
    quiz_score_snapshot: Decimal
    status: ApplicationStatus
    applied_at: datetime

    model_config = {"from_attributes": True}


class ApplicantProfileInfo(BaseModel):
    display_name: str
    avg_rating: Decimal
    review_count: int
    availability_status: str


class ApplicantUserInfo(BaseModel):
    email: str


class ApplicantResponse(BaseModel):
    application_id: UUID
    applied_at: datetime
    quiz_score_snapshot: Decimal
    status: ApplicationStatus
    user: ApplicantUserInfo
    profile: ApplicantProfileInfo


class ApplicantListResponse(BaseModel):
    items: list[ApplicantResponse]


def build_applicant_response(
    application_id: UUID,
    applied_at: datetime,
    quiz_score_snapshot: Decimal,
    status: ApplicationStatus,
    email: str,
    display_name: str,
    avg_rating: Decimal,
    review_count: int,
    available_for_work: bool,
) -> ApplicantResponse:
    return ApplicantResponse(
        application_id=application_id,
        applied_at=applied_at,
        quiz_score_snapshot=quiz_score_snapshot,
        status=status,
        user=ApplicantUserInfo(email=email),
        profile=ApplicantProfileInfo(
            display_name=display_name,
            avg_rating=avg_rating,
            review_count=review_count,
            availability_status=serialize_availability(available_for_work),
        ),
    )
