from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user, get_optional_current_user, require_client, require_freelancer
from app.db.engine import async_session_maker, get_async_session
from app.models.enums import ApplicationStatus, ConversationPhase, JobStatus, UserRole
from app.models.job import Application, Job, JobRequiredSkill
from app.models.messaging import CompletionSignal, Conversation
from app.models.skill import Skill, SkillBadge
from app.models.user import FreelancerProfile, User
from app.schemas.job import (
    ApplicantListResponse,
    ApplicantResponse,
    ApplicationResponse,
    JobCreate,
    JobListResponse,
    JobResponse,
    SelectApplicantRequest,
    SelectApplicantResponse,
    build_applicant_response,
)
from app.schemas.skill import SkillResponse
from app.schemas.upload import FileUploadResponse
from app.services.applications import select_applicant_for_job
from app.services.chat_events import notify_conversation_created, notify_conversation_locked
from app.services.uploads import delete_upload_if_local, save_image_upload
from app.utils.applicant_ranking import compute_composite_score
from app.utils.enums import enum_to_str
from app.utils.response_cache import get_cached, invalidate_prefix, set_cached

router = APIRouter(prefix="/jobs", tags=["jobs"])


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


async def _bulk_get_job_required_skills(
    session: AsyncSession, job_ids: list[UUID]
) -> dict[UUID, list[SkillResponse]]:
    if not job_ids:
        return {}
    result = await session.execute(
        select(JobRequiredSkill.job_id, Skill)
        .join(Skill, JobRequiredSkill.skill_id == Skill.id)
        .where(JobRequiredSkill.job_id.in_(job_ids))
        .order_by(Skill.name.asc())
    )
    skills_by_job: dict[UUID, list[SkillResponse]] = {job_id: [] for job_id in job_ids}
    for job_id, skill in result.all():
        skills_by_job[job_id].append(SkillResponse.model_validate(skill))
    return skills_by_job


def _job_to_response(
    job: Job,
    required_skills: list[SkillResponse],
    *,
    viewer_has_applied: bool = False,
) -> JobResponse:
    return JobResponse(
        id=job.id,
        client_id=job.client_id,
        title=job.title,
        thumbnail_url=job.thumbnail_url,
        description=job.description,
        requirements_education=job.requirements_education,
        requirements_experience=job.requirements_experience,
        requirements_additional=job.requirements_additional,
        responsibilities=job.responsibilities,
        about_role=job.about_role,
        salary_amount=job.salary_amount,
        salary_negotiable=job.salary_negotiable,
        other_benefits=job.other_benefits,
        company_name=job.company_name,
        company_description=job.company_description,
        deliverables=job.deliverables,
        budget=job.budget,
        timeline=job.timeline,
        status=job.status,
        posted_at=job.posted_at,
        updated_at=job.updated_at,
        required_skills=required_skills,
        viewer_has_applied=viewer_has_applied,
    )


async def _build_job_response(
    session: AsyncSession,
    job: Job,
    current_user: User | None = None,
) -> JobResponse:
    required_skills = await _get_job_required_skills(session, job.id)
    viewer_has_applied = False
    if current_user is not None and current_user.role == UserRole.freelancer:
        profile_result = await session.execute(
            select(FreelancerProfile.id).where(FreelancerProfile.user_id == current_user.id)
        )
        profile_id = profile_result.scalar_one_or_none()
        if profile_id is not None:
            applied_result = await session.execute(
                select(Application.id).where(
                    Application.freelancer_id == profile_id,
                    Application.job_id == job.id,
                )
            )
            viewer_has_applied = applied_result.scalar_one_or_none() is not None
    return _job_to_response(job, required_skills, viewer_has_applied=viewer_has_applied)


async def _build_job_list_responses(
    session: AsyncSession, jobs: list[Job]
) -> list[JobResponse]:
    skills_by_job = await _bulk_get_job_required_skills(session, [job.id for job in jobs])
    return [_job_to_response(job, skills_by_job.get(job.id, [])) for job in jobs]


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


async def _can_view_job(
    session: AsyncSession, job: Job, user: User | None
) -> bool:
    if job.status == JobStatus.open:
        return True
    if user is None:
        return False
    if job.client_id == user.id:
        return True

    profile_result = await session.execute(
        select(FreelancerProfile).where(FreelancerProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        return False

    accepted_result = await session.execute(
        select(Application.id).where(
            Application.job_id == job.id,
            Application.freelancer_id == profile.id,
            Application.status == ApplicationStatus.accepted,
        )
    )
    return accepted_result.scalar_one_or_none() is not None


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

    description = payload.description or payload.about_role
    deliverables = payload.deliverables or payload.responsibilities
    budget = (
        payload.budget
        if payload.budget is not None
        else (payload.salary_amount or Decimal("0"))
    )
    timeline = payload.timeline or "Flexible"

    job = Job(
        client_id=current_user.id,
        title=payload.title,
        thumbnail_url=payload.thumbnail_url,
        description=description,
        requirements_education=payload.requirements_education,
        requirements_experience=payload.requirements_experience,
        requirements_additional=payload.requirements_additional,
        responsibilities=payload.responsibilities,
        about_role=payload.about_role,
        salary_amount=payload.salary_amount,
        salary_negotiable=payload.salary_negotiable,
        other_benefits=payload.other_benefits,
        company_name=payload.company_name,
        company_description=payload.company_description,
        deliverables=deliverables,
        budget=budget,
        timeline=timeline,
    )
    session.add(job)
    await session.flush()

    for skill_id in payload.required_skill_ids:
        session.add(JobRequiredSkill(job_id=job.id, skill_id=skill_id))

    invalidate_prefix("jobs:list:")
    return await _build_job_response(session, job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    q: str | None = Query(default=None, description="Search job title"),
    skill_id: UUID | None = Query(default=None),
    company_name: str | None = Query(default=None),
    status_filter: JobStatus | None = Query(default=JobStatus.open, alias="status"),
    min_salary: Decimal | None = Query(default=None, ge=0),
    max_salary: Decimal | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> JobListResponse:
    cache_key = (
        f"jobs:list:{q}:{skill_id}:{company_name}:{status_filter}:"
        f"{min_salary}:{max_salary}:{page}:{limit}"
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    async with async_session_maker() as session:
        query = (
            select(Job)
            .join(User, Job.client_id == User.id)
            .where(
                User.is_deleted.is_(False),
                User.is_banned.is_(False),
            )
        )
        count_query = (
            select(func.count())
            .select_from(Job)
            .join(User, Job.client_id == User.id)
            .where(
                User.is_deleted.is_(False),
                User.is_banned.is_(False),
            )
        )

        if status_filter is not None:
            query = query.where(Job.status == status_filter)
            count_query = count_query.where(Job.status == status_filter)

        if q:
            pattern = f"%{q.strip()}%"
            query = query.where(Job.title.ilike(pattern))
            count_query = count_query.where(Job.title.ilike(pattern))
        if company_name:
            pattern = f"%{company_name.strip()}%"
            query = query.where(Job.company_name.ilike(pattern))
            count_query = count_query.where(Job.company_name.ilike(pattern))
        if skill_id is not None:
            query = query.join(JobRequiredSkill).where(JobRequiredSkill.skill_id == skill_id)
            count_query = count_query.join(JobRequiredSkill).where(
                JobRequiredSkill.skill_id == skill_id
            )
        if min_salary is not None:
            salary_clause = (Job.salary_negotiable.is_(True)) | (Job.salary_amount >= min_salary)
            query = query.where(salary_clause)
            count_query = count_query.where(salary_clause)
        if max_salary is not None:
            salary_clause = Job.salary_negotiable.is_(True) | (
                Job.salary_amount.is_not(None) & (Job.salary_amount <= max_salary)
            )
            query = query.where(salary_clause)
            count_query = count_query.where(salary_clause)

        total = int((await session.execute(count_query)).scalar_one())

        result = await session.execute(
            query.order_by(Job.posted_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        jobs = result.scalars().unique().all()
        items = await _build_job_list_responses(session, jobs)
        return set_cached(cache_key, JobListResponse(items=items, page=page, limit=limit, total=total))


@router.get("/mine", response_model=JobListResponse)
async def list_my_jobs(
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> JobListResponse:
    query = select(Job).where(Job.client_id == current_user.id)
    count_query = (
        select(func.count()).select_from(Job).where(Job.client_id == current_user.id)
    )

    if status_filter is not None:
        query = query.where(Job.status == status_filter)
        count_query = count_query.where(Job.status == status_filter)

    total = int((await session.execute(count_query)).scalar_one())
    result = await session.execute(
        query.order_by(Job.posted_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    jobs = result.scalars().all()
    items = await _build_job_list_responses(session, jobs)
    return JobListResponse(items=items, page=page, limit=limit, total=total)


@router.post("/thumbnail", response_model=FileUploadResponse)
async def upload_job_thumbnail_draft(
    current_user: Annotated[User, Depends(require_client)],
    file: Annotated[UploadFile, File(...)],
) -> FileUploadResponse:
    settings = get_settings()
    url = await save_image_upload(
        file,
        owner_id=current_user.id,
        category="jobs/thumbnails",
        max_bytes=settings.MAX_IMAGE_SIZE_BYTES,
    )
    return FileUploadResponse(url=url)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> JobResponse:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None or not await _can_view_job(session, job, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await _build_job_response(session, job, current_user)


@router.post("/{job_id}/thumbnail", response_model=FileUploadResponse)
async def upload_job_thumbnail(
    job_id: UUID,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    file: Annotated[UploadFile, File(...)],
) -> FileUploadResponse:
    settings = get_settings()
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this job",
        )

    url = await save_image_upload(
        file,
        owner_id=current_user.id,
        category=f"jobs/{job_id}/thumbnail",
        max_bytes=settings.MAX_IMAGE_SIZE_BYTES,
    )
    delete_upload_if_local(job.thumbnail_url)
    job.thumbnail_url = url
    job.updated_at = datetime.now(timezone.utc)
    session.add(job)
    await session.refresh(job)
    return FileUploadResponse(url=url)


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

    existing_result = await session.execute(
        select(Application.id).where(
            Application.freelancer_id == profile.id,
            Application.job_id == job_id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already applied to this job",
        )

    required_result = await session.execute(
        select(JobRequiredSkill.skill_id).where(JobRequiredSkill.job_id == job_id)
    )
    required_skill_ids = set(required_result.scalars().all())

    badges_result = await session.execute(
        select(SkillBadge).where(
            SkillBadge.profile_id == profile.id,
            SkillBadge.skill_id.in_(required_skill_ids),
        )
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

    relevant_badges = badges
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


@router.post("/{job_id}/select", response_model=SelectApplicantResponse)
async def select_applicant(
    job_id: UUID,
    payload: SelectApplicantRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SelectApplicantResponse:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    application, conversation, message = await select_applicant_for_job(
        session,
        job=job,
        client=current_user,
        application_id=payload.application_id,
    )
    await notify_conversation_created(
        request.app,
        conversation=conversation,
        message=message,
        job_title=job.title,
    )
    return SelectApplicantResponse(
        application_id=application.id,
        status=application.status,
        conversation=conversation,
        message=message,
    )


@router.get("/{job_id}/applicants", response_model=ApplicantListResponse)
async def list_applicants(
    job_id: UUID,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
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

    result = await session.execute(
        select(Application, FreelancerProfile, User)
        .join(FreelancerProfile, Application.freelancer_id == FreelancerProfile.id)
        .join(User, FreelancerProfile.user_id == User.id)
        .where(
            Application.job_id == job_id,
            User.is_banned.is_(False),
            User.is_deleted.is_(False),
        )
    )

    ranked: list[tuple[Decimal, ApplicantResponse]] = []
    for application, profile, user in result.all():
        composite_score, no_review_experience = compute_composite_score(
            quiz_score=application.quiz_score_snapshot,
            avg_rating=profile.avg_rating,
            review_count=profile.review_count,
        )
        ranked.append(
            (
                composite_score,
                build_applicant_response(
                    application_id=application.id,
                    applied_at=application.applied_at,
                    quiz_score_snapshot=application.quiz_score_snapshot,
                    composite_score=composite_score,
                    status=application.status,
                    email=user.email,
                    display_name=profile.display_name,
                    avg_rating=profile.avg_rating,
                    review_count=profile.review_count,
                    available_for_work=profile.available_for_work,
                    no_review_experience=no_review_experience,
                ),
            )
        )

    ranked.sort(key=lambda item: item[0], reverse=True)
    return ApplicantListResponse(items=[item[1] for item in ranked])


@router.post("/{job_id}/complete", status_code=status.HTTP_200_OK)
async def signal_completion(
    job_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status not in (JobStatus.filled, JobStatus.pending_confirmation):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot signal completion for job with status {enum_to_str(job.status)}",
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
            await notify_conversation_locked(
                request.app,
                conversation=conversation,
            )

    return {"status": "completion signalled"}
