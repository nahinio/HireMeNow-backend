from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.utils.availability import serialize_availability


class FreelancerProfileUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    available_for_work: bool | None = None


class FreelancerProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    bio: str
    avg_rating: Decimal
    review_count: int
    updated_at: datetime
    available_for_work: bool = Field(exclude=True)

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def availability_status(self) -> str:
        return serialize_availability(self.available_for_work)


class PortfolioLinkCreate(BaseModel):
    label: str
    url: str
    position: int


class PortfolioLinkResponse(BaseModel):
    id: UUID
    profile_id: UUID
    label: str
    url: str
    position: int

    model_config = {"from_attributes": True}
