from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    skill_id: UUID
    name: str = Field(min_length=1)
    thumbnail_url: str | None = None
    link: str = Field(min_length=1)
    is_active: bool = True


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    thumbnail_url: str | None = None
    link: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class CourseResponse(BaseModel):
    id: UUID
    skill_id: UUID
    skill_name: str | None = None
    name: str
    thumbnail_url: str | None = None
    link: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseListResponse(BaseModel):
    items: list[CourseResponse]
    page: int
    limit: int
    total: int


class RecommendedCourseResponse(BaseModel):
    id: UUID
    skill_id: UUID
    skill_name: str
    name: str
    thumbnail_url: str | None = None
    link: str

    model_config = {"from_attributes": True}
