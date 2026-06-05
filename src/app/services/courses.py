from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.skill import Skill


async def count_active_courses_for_skill(session: AsyncSession, skill_id: UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Course)
        .where(Course.skill_id == skill_id, Course.is_active.is_(True))
    )
    return int(result.scalar_one())


async def ensure_skill_has_minimum_courses(
    session: AsyncSession,
    skill_id: UUID,
    *,
    minimum: int = 1,
) -> None:
    count = await count_active_courses_for_skill(session, skill_id)
    if count < minimum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Skill requires at least {minimum} active course(s) before publishing a quiz",
        )


async def ensure_can_remove_course(session: AsyncSession, course: Course) -> None:
    if not course.is_active:
        return

    count = await count_active_courses_for_skill(session, course.skill_id)
    if count <= 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Each skill must keep at least one active course",
        )


async def get_active_courses_for_skill(
    session: AsyncSession, skill_id: UUID
) -> list[tuple[Course, Skill]]:
    result = await session.execute(
        select(Course, Skill)
        .join(Skill, Course.skill_id == Skill.id)
        .where(
            Course.skill_id == skill_id,
            Course.is_active.is_(True),
            Skill.is_active.is_(True),
        )
        .order_by(Course.name.asc())
    )
    return list(result.all())


def build_course_response(course: Course, skill_name: str | None = None) -> dict:
    return {
        "id": course.id,
        "skill_id": course.skill_id,
        "skill_name": skill_name,
        "name": course.name,
        "thumbnail_url": course.thumbnail_url,
        "link": course.link,
        "is_active": course.is_active,
        "created_at": course.created_at,
    }
