from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ApplicationStatus, JobStatus
from app.schemas.messaging import ConversationResponse, MessageResponse
from app.schemas.skill import SkillResponse
from app.utils.availability import serialize_availability


class JobCreate(BaseModel):
    title: str
    required_skill_ids: list[UUID] = Field(min_length=1)
    thumbnail_url: str | None = None
    requirements_education: str = ""
    requirements_experience: str = ""
    requirements_additional: str = ""
    responsibilities: str = ""
    about_role: str = ""
    salary_amount: Decimal | None = None
    salary_negotiable: bool = False
    other_benefits: str = ""
    company_name: str = ""
    company_description: str = ""
    description: str | None = None
    deliverables: str | None = None
    budget: Decimal | None = None
    timeline: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> Self:
        using_legacy = self.description is not None
        if using_legacy:
            return self

        if not self.about_role.strip():
            raise ValueError("about_role is required")
        if not self.responsibilities.strip():
            raise ValueError("responsibilities is required")
        if not self.company_name.strip():
            raise ValueError("company_name is required")
        if not self.salary_negotiable and self.salary_amount is None:
            raise ValueError("salary_amount is required unless salary_negotiable is true")
        return self


class JobResponse(BaseModel):
    id: UUID
    client_id: UUID
    title: str
    thumbnail_url: str | None = None
    description: str
    requirements_education: str = ""
    requirements_experience: str = ""
    requirements_additional: str = ""
    responsibilities: str = ""
    about_role: str = ""
    salary_amount: Decimal | None = None
    salary_negotiable: bool = False
    other_benefits: str = ""
    company_name: str = ""
    company_description: str = ""
    deliverables: str
    budget: Decimal
    timeline: str
    status: JobStatus
    posted_at: datetime
    updated_at: datetime
    required_skills: list[SkillResponse] = Field(default_factory=list)
    viewer_has_applied: bool = False

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
    available_for_work: bool
    no_review_experience: bool


class ApplicantUserInfo(BaseModel):
    email: str


class ApplicantResponse(BaseModel):
    application_id: UUID
    applied_at: datetime
    quiz_score_snapshot: Decimal
    composite_score: Decimal
    status: ApplicationStatus
    user: ApplicantUserInfo
    profile: ApplicantProfileInfo


class ApplicantListResponse(BaseModel):
    items: list[ApplicantResponse]


class SelectApplicantRequest(BaseModel):
    application_id: UUID


class SelectApplicantResponse(BaseModel):
    application_id: UUID
    status: ApplicationStatus
    conversation: ConversationResponse
    message: MessageResponse


def build_applicant_response(
    application_id: UUID,
    applied_at: datetime,
    quiz_score_snapshot: Decimal,
    composite_score: Decimal,
    status: ApplicationStatus,
    email: str,
    display_name: str,
    avg_rating: Decimal,
    review_count: int,
    available_for_work: bool,
    no_review_experience: bool,
) -> ApplicantResponse:
    return ApplicantResponse(
        application_id=application_id,
        applied_at=applied_at,
        quiz_score_snapshot=quiz_score_snapshot,
        composite_score=composite_score,
        status=status,
        user=ApplicantUserInfo(email=email),
        profile=ApplicantProfileInfo(
            display_name=display_name,
            avg_rating=avg_rating,
            review_count=review_count,
            availability_status=serialize_availability(available_for_work),
            available_for_work=available_for_work,
            no_review_experience=no_review_experience,
        ),
    )
