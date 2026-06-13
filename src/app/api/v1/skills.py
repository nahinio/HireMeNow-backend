from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.db.engine import async_session_maker
from app.models.skill import Question, Quiz, Skill
from app.schemas.skill import SkillListResponse, SkillPublicResponse, SkillQuizSummary
from app.utils.response_cache import get_cached, set_cached

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=SkillListResponse)
async def list_skills(
    q: str | None = Query(default=None, description="Search skill name"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> SkillListResponse:
    cache_key = f"skills:list:{q}:{page}:{limit}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    async with async_session_maker() as session:
        query = select(Skill).where(Skill.is_active.is_(True))
        count_query = select(func.count()).select_from(Skill).where(Skill.is_active.is_(True))

        if q:
            pattern = f"%{q.strip()}%"
            query = query.where(Skill.name.ilike(pattern))
            count_query = count_query.where(Skill.name.ilike(pattern))

        total = int((await session.execute(count_query)).scalar_one())
        skills = (
            await session.execute(
                query.order_by(Skill.name.asc()).offset((page - 1) * limit).limit(limit)
            )
        ).scalars().all()

        skill_ids = [skill.id for skill in skills]
        quiz_by_skill: dict[UUID, Quiz] = {}
        question_counts: dict[UUID, int] = {}

        if skill_ids:
            quiz_result = await session.execute(
                select(Quiz).where(
                    Quiz.skill_id.in_(skill_ids),
                    Quiz.published.is_(True),
                )
            )
            quizzes = quiz_result.scalars().all()
            quiz_by_skill = {quiz.skill_id: quiz for quiz in quizzes}

            if quizzes:
                quiz_ids = [quiz.id for quiz in quizzes]
                counts_result = await session.execute(
                    select(Question.quiz_id, func.count())
                    .where(Question.quiz_id.in_(quiz_ids))
                    .group_by(Question.quiz_id)
                )
                question_counts = {quiz_id: int(count) for quiz_id, count in counts_result.all()}

        items = [
            SkillPublicResponse(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                quiz=(
                    SkillQuizSummary(
                        quiz_id=quiz_by_skill[skill.id].id,
                        pass_threshold=quiz_by_skill[skill.id].pass_threshold,
                        question_count=question_counts.get(quiz_by_skill[skill.id].id, 0),
                    )
                    if skill.id in quiz_by_skill
                    else None
                ),
            )
            for skill in skills
        ]

        return set_cached(cache_key, SkillListResponse(items=items, page=page, limit=limit, total=total))
