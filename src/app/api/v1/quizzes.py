from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_freelancer
from app.db.engine import get_async_session
from app.models.enums import QuizResult
from app.models.skill import AnswerOption, Question, Quiz, QuizAttempt, SkillBadge
from app.models.user import FreelancerProfile, User
from app.schemas.skill import QuizAttemptAnswer, QuizAttemptResponse
from app.services.quiz_grading import grade_quiz_attempt

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


async def _get_freelancer_profile(
    session: AsyncSession, user_id: UUID
) -> FreelancerProfile:
    result = await session.execute(
        select(FreelancerProfile).where(FreelancerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer profile not found",
        )
    return profile


@router.post("/{quiz_id}/attempt", response_model=QuizAttemptResponse)
async def attempt_quiz(
    quiz_id: UUID,
    payload: list[QuizAttemptAnswer],
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizAttemptResponse:
    quiz_result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = quiz_result.scalar_one_or_none()
    if quiz is None or not quiz.published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    questions_result = await session.execute(
        select(Question).where(Question.quiz_id == quiz_id)
    )
    questions = questions_result.scalars().all()
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quiz has no questions",
        )

    question_ids = {question.id for question in questions}
    options_result = await session.execute(
        select(AnswerOption).where(AnswerOption.question_id.in_(question_ids))
    )
    options = options_result.scalars().all()
    options_by_id = {option.id: option for option in options}
    correct_option_ids = {option.id for option in options if option.is_correct}

    correct_count = 0
    for answer in payload:
        option = options_by_id.get(answer.selected_option_id)
        if option is not None and option.id in correct_option_ids:
            if option.question_id == answer.question_id:
                correct_count += 1

    total_questions = len(questions)
    score, passed = grade_quiz_attempt(
        total_questions=total_questions,
        correct_count=correct_count,
        pass_threshold=quiz.pass_threshold,
    )
    profile = await _get_freelancer_profile(session, current_user.id)

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        profile_id=profile.id,
        score=score,
        result=QuizResult.PASS if passed else QuizResult.FAIL,
    )
    session.add(attempt)

    if passed:
        badge_result = await session.execute(
            select(SkillBadge).where(
                SkillBadge.profile_id == profile.id,
                SkillBadge.skill_id == quiz.skill_id,
            )
        )
        if badge_result.scalar_one_or_none() is None:
            session.add(
                SkillBadge(
                    profile_id=profile.id,
                    skill_id=quiz.skill_id,
                    score=score,
                    earned_at=datetime.now(timezone.utc),
                )
            )
        return QuizAttemptResponse(result="pass", score=float(score))

    return QuizAttemptResponse(
        result="fail",
        score=float(score),
        resources=["Review skill materials and retry the quiz."],
    )
