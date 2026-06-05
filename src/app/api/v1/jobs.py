from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_client, require_freelancer
from app.db.engine import get_async_session
from app.models.enums import ApplicationStatus, ConversationPhase, JobStatus
from app.models.job import Application, Job, JobRequiredSkill
from app.models.messaging import CompletionSignal, Conversation
from app.models.skill import Skill, SkillBadge
from app.models.user import FreelancerProfile, User
from app.schemas.job import (
    ApplicantListResponse,
    ApplicationResponse,
    JobCreate,
    JobListResponse,
    JobResponse,
    build_applicant_response,
)
from app.schemas.skill import SkillResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

SORT_COLUMNS = {
    "quiz_score_snapshot": Application.quiz_score_snapshot,
    "avg_rating": FreelancerProfile.avg_rating,
    "applied_at": Application.applied_at,
}


async def _get_job_required_skills(
    session: AsyncSession, job_id: UUID
) -> list[SkillResponse]:
    result = await session.execute(
        select(Skill)
        .join(JobRequiredSkill, JobRequiredSkill.skill_id == Skill.id)
        .where(JobRequiredSkill.job_id == job_id)
    )
    skills = result.scalars().all()
    return [SkillResponse.model_validate(skill) for skill in skills]


async def _build_job_response(session: AsyncSession, job: Job) -> JobResponse:
    required_skills = await _get_job_required_skills(session, job.id)
    return JobResponse(
        id=job.id,
        client_id=job.client_id,
        title=job.title,
        description=job.description,
        deliverables=job.deliverables,
        budget=job.budget,
        timeline=job.timeline,
        status=job.status,
        posted_at=job.posted_at,
        updated_at=job.updated_at,
        required_skills=required_skills,
    )


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


async def _verify_job_party(
    session: AsyncSession, job: Job, user: User
) -> None:
    if job.client_id == user.id:
        return

    profile = await _get_freelancer_profile(session, user.id)
    accepted_result = await session.execute(
        select(Application).where(
            Application.job_id == job.id,
            Application.freelancer_id == profile.id,
            Application.status == ApplicationStatus.accepted,
        )
    )
    if accepted_result.scalar_one_or_none() is not None:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not a party to this job",
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> JobResponse:
    skills_result = await session.execute(
        select(Skill).where(
            Skill.id.in_(payload.required_skill_ids),
            Skill.is_active.is_(True),
        )
    )
    skills = skills_result.scalars().all()
    if len(skills) != len(set(payload.required_skill_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more skill IDs are invalid or inactive",
        )

    job = Job(
        client_id=current_user.id,
        title=payload.title,
        description=payload.description,
        deliverables=payload.deliverables,
        budget=payload.budget,
        timeline=payload.timeline,
    )
    session.add(job)
    await session.flush()

    for skill_id in payload.required_skill_ids:
        session.add(JobRequiredSkill(job_id=job.id, skill_id=skill_id))

    return await _build_job_response(session, job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> JobListResponse:
    count_result = await session.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.open)
    )
    total = int(count_result.scalar_one())

    result = await session.execute(
        select(Job)
        .where(Job.status == JobStatus.open)
        .order_by(Job.posted_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    jobs = result.scalars().all()
    items = [await _build_job_response(session, job) for job in jobs]
    return JobListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> JobResponse:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await _build_job_response(session, job)


@router.post("/{job_id}/apply", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Application:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None or job.status != JobStatus.open:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    profile = await _get_freelancer_profile(session, current_user.id)

    required_result = await session.execute(
        select(JobRequiredSkill.skill_id).where(JobRequiredSkill.job_id == job_id)
    )
    required_skill_ids = set(required_result.scalars().all())

    badges_result = await session.execute(
        select(SkillBadge).where(SkillBadge.profile_id == profile.id)
    )
    badges = badges_result.scalars().all()
    badge_skill_ids = {badge.skill_id for badge in badges}

    missing_ids = required_skill_ids - badge_skill_ids
    if missing_ids:
        skills_result = await session.execute(
            select(Skill).where(Skill.id.in_(missing_ids))
        )
        missing_names = [skill.name for skill in skills_result.scalars().all()]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "Missing required skill badges",
                "missing_skills": missing_names,
            },
        )

    existing_result = await session.execute(
        select(Application).where(
            Application.freelancer_id == profile.id,
            Application.job_id == job_id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already applied to this job",
        )

    relevant_badges = [badge for badge in badges if badge.skill_id in required_skill_ids]
    quiz_score_snapshot = max((badge.score for badge in relevant_badges), default=Decimal("0"))

    application = Application(
        freelancer_id=profile.id,
        job_id=job_id,
        quiz_score_snapshot=quiz_score_snapshot,
    )
    session.add(application)
    await session.flush()
    await session.refresh(application)
    return application


@router.get("/{job_id}/applicants", response_model=ApplicantListResponse)
async def list_applicants(
    job_id: UUID,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    sort_by: str = Query(default="applied_at"),
    order: str = Query(default="desc"),
) -> ApplicantListResponse:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view applicants",
        )

    if sort_by not in SORT_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort_by value: {sort_by}",
        )

    sort_column = SORT_COLUMNS[sort_by]
    if order == "desc":
        order_clause = sort_column.desc()
    elif order == "asc":
        order_clause = sort_column.asc()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid order value: {order}",
        )

    result = await session.execute(
        select(Application, FreelancerProfile, User)
        .join(FreelancerProfile, Application.freelancer_id == FreelancerProfile.id)
        .join(User, FreelancerProfile.user_id == User.id)
        .where(Application.job_id == job_id, User.is_banned.is_(False))
        .order_by(order_clause)
    )

    items = [
        build_applicant_response(
            application_id=application.id,
            applied_at=application.applied_at,
            quiz_score_snapshot=application.quiz_score_snapshot,
            status=application.status,
            email=user.email,
            display_name=profile.display_name,
            avg_rating=profile.avg_rating,
            review_count=profile.review_count,
            available_for_work=profile.available_for_work,
        )
        for application, profile, user in result.all()
    ]
    return ApplicantListResponse(items=items)


@router.post("/{job_id}/complete", status_code=status.HTTP_200_OK)
async def signal_completion(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status not in (JobStatus.open, JobStatus.pending_confirmation):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot signal completion for job with status {job.status.value}",
        )

    await _verify_job_party(session, job, current_user)

    existing_signal = await session.execute(
        select(CompletionSignal).where(
            CompletionSignal.job_id == job_id,
            CompletionSignal.signalled_by == current_user.id,
        )
    )
    if existing_signal.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completion already signalled",
        )

    session.add(
        CompletionSignal(job_id=job_id, signalled_by=current_user.id)
    )
    await session.flush()

    count_result = await session.execute(
        select(func.count())
        .select_from(CompletionSignal)
        .where(CompletionSignal.job_id == job_id)
    )
    signal_count = int(count_result.scalar_one())

    if signal_count == 1:
        job.status = JobStatus.pending_confirmation
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)
    elif signal_count >= 2:
        conversations_result = await session.execute(
            select(Conversation).where(Conversation.job_id == job_id)
        )
        for conversation in conversations_result.scalars().all():
            conversation.phase = ConversationPhase.is_locked
            session.add(conversation)

    return {"status": "completion signalled"}
