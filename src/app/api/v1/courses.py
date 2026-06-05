from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_async_session
from app.models.course import Course
from app.models.skill import Skill
from app.schemas.course import CourseListResponse, CourseResponse

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=CourseListResponse)
async def list_courses(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    q: str | None = Query(default=None, description="Search course name"),
    skill_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> CourseListResponse:
    query = (
        select(Course, Skill)
        .join(Skill, Course.skill_id == Skill.id)
        .where(
            Course.is_active.is_(True),
            Skill.is_active.is_(True),
        )
    )
    count_query = (
        select(func.count())
        .select_from(Course)
        .join(Skill, Course.skill_id == Skill.id)
        .where(
            Course.is_active.is_(True),
            Skill.is_active.is_(True),
        )
    )

    if skill_id is not None:
        query = query.where(Course.skill_id == skill_id)
        count_query = count_query.where(Course.skill_id == skill_id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Course.name.ilike(pattern))
        count_query = count_query.where(Course.name.ilike(pattern))

    total = int((await session.execute(count_query)).scalar_one())
    result = await session.execute(
        query.order_by(Skill.name.asc(), Course.name.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    )

    items = [
        CourseResponse(
            id=course.id,
            skill_id=course.skill_id,
            skill_name=skill.name,
            name=course.name,
            thumbnail_url=course.thumbnail_url,
            link=course.link,
            is_active=course.is_active,
            created_at=course.created_at,
        )
        for course, skill in result.all()
    ]
    return CourseListResponse(items=items, page=page, limit=limit, total=total)
