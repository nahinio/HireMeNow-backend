from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ClientProfileUpdate(BaseModel):
    company_name: str | None = None
    bio: str | None = None
    profile_picture_url: str | None = None
    company_link: str | None = None


class ClientProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    company_name: str
    bio: str
    profile_picture_url: str | None = None
    company_link: str | None = None
    avg_rating: Decimal
    review_count: int
    updated_at: datetime

    model_config = {"from_attributes": True}
