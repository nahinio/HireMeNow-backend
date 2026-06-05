from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.engine import get_async_session
from app.models.enums import (
    ApplicationStatus,
    DisputeStatus,
    JobStatus,
    UserRole,
)
from app.models.job import Application, Job
from app.models.review import Dispute, Review
from app.models.skill import AnswerOption, Question, Quiz, Skill
from app.models.user import (
    ClientProfile,
    FreelancerProfile,
    TokenBlocklist,
    User,
)
from app.schemas.review import (
    BanRequest,
    BanResponse,
    DisputeListResponse,
    DisputeResolveRequest,
    DisputeResponse,
    ReviewDeleteResponse,
)
from app.schemas.skill import (
    AnswerOptionCreate,
    AnswerOptionResponse,
    QuestionCreate,
    QuestionResponse,
    QuizCreate,
    QuizResponse,
    SkillCreate,
    SkillResponse,
)
from app.services.reviews import recalculate_profile_ratings, update_profile_ratings_for_user
from app.utils.enums import enum_to_str

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Skill:
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
        is_active=payload.is_active,
        created_by=current_user.id,
    )
    session.add(skill)
    await session.flush()
    await session.refresh(skill)
    return skill


@router.post("/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    payload: QuizCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizResponse:
    skill_result = await session.execute(select(Skill).where(Skill.id == payload.skill_id))
    skill = skill_result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    existing_quiz = await session.execute(
        select(Quiz).where(Quiz.skill_id == payload.skill_id)
    )
    if existing_quiz.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quiz already exists for this skill",
        )

    quiz = Quiz(
        skill_id=payload.skill_id,
        pass_threshold=payload.pass_threshold,
        published=payload.published,
    )
    session.add(quiz)
    await session.flush()
    return QuizResponse(
        id=quiz.id,
        skill_id=quiz.skill_id,
        skill_name=skill.name,
        pass_threshold=quiz.pass_threshold,
        published=quiz.published,
    )


@router.post(
    "/quizzes/{quiz_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    quiz_id: UUID,
    payload: QuestionCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Question:
    quiz_result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
    if quiz_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    question = Question(
        quiz_id=quiz_id,
        body=payload.body,
        position=payload.position,
    )
    session.add(question)
    await session.flush()
    await session.refresh(question)
    return question


@router.post(
    "/questions/{question_id}/options",
    response_model=AnswerOptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_answer_option(
    question_id: UUID,
    payload: AnswerOptionCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AnswerOption:
    question_result = await session.execute(
        select(Question).where(Question.id == question_id)
    )
    if question_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )

    if payload.is_correct:
        existing_correct = await session.execute(
            select(AnswerOption).where(
                AnswerOption.question_id == question_id,
                AnswerOption.is_correct.is_(True),
            )
        )
        if existing_correct.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Question already has a correct answer option",
            )

    option = AnswerOption(
        question_id=question_id,
        body=payload.body,
        is_correct=payload.is_correct,
    )
    session.add(option)
    await session.flush()
    await session.refresh(option)
    return option


@router.get("/disputes", response_model=DisputeListResponse)
async def list_disputes(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    status_filter: DisputeStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> DisputeListResponse:
    query = select(Dispute)
    count_query = select(func.count()).select_from(Dispute)

    if status_filter is not None:
        query = query.where(Dispute.status == status_filter)
        count_query = count_query.where(Dispute.status == status_filter)

    total_result = await session.execute(count_query)
    total = int(total_result.scalar_one())

    result = await session.execute(
        query.order_by(Dispute.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    items = result.scalars().all()
    return DisputeListResponse(
        items=[DisputeResponse.model_validate(item) for item in items],
        page=page,
        limit=limit,
        total=total,
    )


@router.patch("/disputes/{dispute_id}", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: UUID,
    payload: DisputeResolveRequest,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Dispute:
    result = await session.execute(select(Dispute).where(Dispute.id == dispute_id))
    dispute = result.scalar_one_or_none()
    if dispute is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")

    if payload.status is not None:
        dispute.status = payload.status
    if payload.resolution_notes is not None:
        dispute.description = (
            f"{dispute.description}\n\nResolution: {payload.resolution_notes}"
        )

    dispute.resolved_by = current_user.id
    dispute.resolved_at = datetime.now(timezone.utc)
    session.add(dispute)

    if payload.new_job_status is not None:
        job_result = await session.execute(select(Job).where(Job.id == dispute.job_id))
        job = job_result.scalar_one()
        job.status = payload.new_job_status
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)

    await session.refresh(dispute)
    return dispute


@router.delete("/reviews/{review_id}", response_model=ReviewDeleteResponse)
async def delete_review(
    review_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ReviewDeleteResponse:
    result = await session.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    review.is_deleted = True
    session.add(review)
    await update_profile_ratings_for_user(session, review.reviewee_id)
    avg_rating, review_count = await recalculate_profile_ratings(session, review.reviewee_id)

    return ReviewDeleteResponse(
        review_id=review.id,
        reviewee_id=review.reviewee_id,
        avg_rating=avg_rating,
        review_count=review_count,
    )


@router.post("/users/{user_id}/ban", response_model=BanResponse)
async def ban_user(
    user_id: UUID,
    payload: BanRequest,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> BanResponse:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_banned = True
    user.ban_reason = payload.ban_reason
    session.add(user)

    blocklist_result = await session.execute(
        select(TokenBlocklist).where(TokenBlocklist.user_id == user_id)
    )
    if blocklist_result.scalar_one_or_none() is None:
        session.add(TokenBlocklist(user_id=user_id))

    pending_deleted = 0
    jobs_closed = 0
    applications_canceled = 0

    if user.role == UserRole.freelancer:
        profile_result = await session.execute(
            select(FreelancerProfile).where(FreelancerProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one()
        delete_result = await session.execute(
            delete(Application).where(
                Application.freelancer_id == profile.id,
                Application.status == ApplicationStatus.pending,
            )
        )
        pending_deleted = delete_result.rowcount or 0
        profile.available_for_work = False
        profile.updated_at = datetime.now(timezone.utc)
        session.add(profile)

    elif user.role == UserRole.client:
        close_result = await session.execute(
            update(Job)
            .where(Job.client_id == user_id, Job.status == JobStatus.open)
            .values(status=JobStatus.closed, updated_at=datetime.now(timezone.utc))
        )
        jobs_closed = close_result.rowcount or 0

        cancel_result = await session.execute(
            update(Application)
            .where(
                Application.job_id.in_(
                    select(Job.id).where(Job.client_id == user_id)
                ),
                Application.status == ApplicationStatus.pending,
            )
            .values(status=ApplicationStatus.canceled)
        )
        applications_canceled = cancel_result.rowcount or 0

    return BanResponse(
        user_id=user.id,
        role=enum_to_str(user.role),
        pending_applications_deleted=pending_deleted,
        jobs_closed=jobs_closed,
        applications_canceled=applications_canceled,
    )
