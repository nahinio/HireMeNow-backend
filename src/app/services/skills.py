from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import AnswerOption, Question, Quiz, Skill
from app.schemas.skill import (
    SkillWithQuizCreate,
    SkillWithQuizResponse,
)
from app.services.courses import ensure_skill_has_minimum_courses


async def create_skill_with_quiz(
    session: AsyncSession,
    *,
    payload: SkillWithQuizCreate,
    created_by: UUID,
) -> SkillWithQuizResponse:
    existing = await session.execute(
        select(Skill).where(func.lower(Skill.name) == payload.name.lower())
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Skill name already exists",
        )

    skill = Skill(
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
        created_by=created_by,
    )
    session.add(skill)
    await session.flush()

    if payload.published:
        await ensure_skill_has_minimum_courses(session, skill.id)

    quiz = Quiz(
        skill_id=skill.id,
        pass_threshold=payload.pass_threshold,
        published=payload.published,
    )
    session.add(quiz)
    await session.flush()

    question_responses = []
    for question_payload in sorted(payload.questions, key=lambda item: item.position):
        question = Question(
            quiz_id=quiz.id,
            body=question_payload.body,
            position=question_payload.position,
        )
        session.add(question)
        await session.flush()

        option_responses = []
        for option_payload in question_payload.options:
            option = AnswerOption(
                question_id=question.id,
                body=option_payload.body,
                is_correct=option_payload.is_correct,
            )
            session.add(option)
            await session.flush()
            option_responses.append(option)

        question_responses.append((question, option_responses))

    await session.refresh(skill)
    await session.refresh(quiz)

    return SkillWithQuizResponse.from_records(
        skill=skill,
        quiz=quiz,
        question_records=question_responses,
    )
