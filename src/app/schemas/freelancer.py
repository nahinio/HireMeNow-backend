from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.utils.availability import serialize_availability


class FreelancerProfileUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    profile_picture_url: str | None = None
    resume_url: str | None = None
    linkedin_url: str | None = None
    contact_email: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    available_for_work: bool | None = None


class FreelancerProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    bio: str
    profile_picture_url: str | None = None
    resume_url: str | None = None
    linkedin_url: str | None = None
    contact_email: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    avg_rating: Decimal
    review_count: int
    updated_at: datetime
    available_for_work: bool = Field(exclude=True)
    portfolio_links: list["PortfolioLinkResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def availability_status(self) -> str:
        return serialize_availability(self.available_for_work)


class PortfolioLinkCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=500)
    position: int = Field(ge=1)


class PortfolioLinkUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    position: int | None = Field(default=None, ge=1)


class PortfolioLinkResponse(BaseModel):
    id: UUID
    profile_id: UUID
    label: str
    url: str
    position: int

    model_config = {"from_attributes": True}


FreelancerProfileResponse.model_rebuild()
