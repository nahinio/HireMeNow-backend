from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_admin
from app.db.engine import get_async_session
from app.models.enums import (
    ApplicationStatus,
    JobStatus,
    ReportStatus,
    UserRole,
)
from app.models.course import Course
from app.models.job import Application, Job, JobRequiredSkill
from app.models.report import UserReport
from app.models.review import Review
from app.models.skill import AnswerOption, Question, Quiz, Skill
from app.models.user import (
    ClientProfile,
    FreelancerProfile,
    TokenBlocklist,
    User,
)
from app.schemas.course import CourseCreate, CourseListResponse, CourseResponse, CourseUpdate
from app.schemas.admin import (
    AdminJobApplicantsResponse,
    AdminJobListResponse,
    AdminJobSummary,
    AdminStatsResponse,
    AdminUserDeleteResponse,
    AdminUserListResponse,
    AdminUserSummary,
)
from app.schemas.job import ApplicantListResponse, JobResponse, build_applicant_response
from app.schemas.report import (
    UserReportListResponse,
    UserReportResolveRequest,
    UserReportResolveResponse,
    UserReportResponse,
)
from app.schemas.review import (
    BanRequest,
    BanResponse,
    ReviewDeleteResponse,
)
from app.schemas.skill import (
    AdminSkillDetailResponse,
    AdminSkillListResponse,
    AnswerOptionCreate,
    AnswerOptionResponse,
    QuestionCreate,
    QuestionResponse,
    QuizCreate,
    QuizResponse,
    QuizUpdate,
    SkillCreate,
    SkillQuizReplace,
    SkillResponse,
    SkillUpdate,
    SkillWithQuizCreate,
    SkillWithQuizResponse,
)
from app.services.admin_stats import get_admin_stats
from app.services.courses import (
    ensure_can_remove_course,
    ensure_skill_has_minimum_courses,
)
from app.services.profile import delete_user_for_report
from app.services.reviews import recalculate_profile_ratings, update_profile_ratings_for_user
from app.services.reports import resolve_user_report
from app.schemas.upload import FileUploadResponse
from app.services.skills import (
    create_skill_with_quiz,
    delete_skill,
    get_skill_detail_admin,
    get_skill_with_quiz,
    list_admin_skills,
    replace_skill_quiz,
    update_skill,
)
from app.services.uploads import delete_upload_if_local, save_image_upload
from app.utils.applicant_ranking import compute_composite_score
from app.utils.enums import enum_to_str

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AdminStatsResponse:
    return await get_admin_stats(session)


async def _build_admin_job_response(session: AsyncSession, job: Job) -> JobResponse:
    skills_result = await session.execute(
        select(Skill)
        .join(JobRequiredSkill, JobRequiredSkill.skill_id == Skill.id)
        .where(JobRequiredSkill.job_id == job.id)
    )
    required_skills = [
        SkillResponse.model_validate(skill) for skill in skills_result.scalars().all()
    ]
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
    )


async def _build_admin_applicant_list(
    session: AsyncSession, job_id: UUID
) -> ApplicantListResponse:
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

    ranked: list[tuple[Decimal, object]] = []
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
        description=payload.description,
        is_active=payload.is_active,
        created_by=current_user.id,
    )
    session.add(skill)
    await session.flush()
    await session.refresh(skill)
    return skill


@router.post(
    "/skills/with-quiz",
    response_model=SkillWithQuizResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_skill_with_quiz_endpoint(
    payload: SkillWithQuizCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SkillWithQuizResponse:
    return await create_skill_with_quiz(
        session,
        payload=payload,
        created_by=current_user.id,
    )


@router.get("/skills", response_model=AdminSkillListResponse)
async def list_skills_admin(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> AdminSkillListResponse:
    return await list_admin_skills(session, page=page, limit=limit)


@router.get("/skills/{skill_id}", response_model=AdminSkillDetailResponse)
async def get_skill_admin(
    skill_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AdminSkillDetailResponse:
    return await get_skill_detail_admin(session, skill_id)


@router.patch("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill_admin(
    skill_id: UUID,
    payload: SkillUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SkillResponse:
    return await update_skill(session, skill_id, payload)


@router.put("/skills/{skill_id}/quiz", response_model=SkillWithQuizResponse)
async def replace_skill_quiz_admin(
    skill_id: UUID,
    payload: SkillQuizReplace,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SkillWithQuizResponse:
    return await replace_skill_quiz(session, skill_id, payload)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill_admin(
    skill_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    await delete_skill(session, skill_id)


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

    if payload.published:
        await ensure_skill_has_minimum_courses(session, payload.skill_id)

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


@router.patch("/quizzes/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: UUID,
    payload: QuizUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> QuizResponse:
    quiz_result = await session.execute(
        select(Quiz, Skill).join(Skill, Quiz.skill_id == Skill.id).where(Quiz.id == quiz_id)
    )
    row = quiz_result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    quiz, skill = row
    if payload.pass_threshold is not None:
        quiz.pass_threshold = payload.pass_threshold
    if payload.published is not None:
        if payload.published and not quiz.published:
            await ensure_skill_has_minimum_courses(session, quiz.skill_id)
        quiz.published = payload.published

    session.add(quiz)
    await session.refresh(quiz)
    return QuizResponse(
        id=quiz.id,
        skill_id=quiz.skill_id,
        skill_name=skill.name,
        pass_threshold=quiz.pass_threshold,
        published=quiz.published,
    )


@router.post("/courses/thumbnail", response_model=FileUploadResponse)
async def upload_course_thumbnail(
    current_user: Annotated[User, Depends(require_admin)],
    file: Annotated[UploadFile, File(...)],
) -> FileUploadResponse:
    settings = get_settings()
    url = await save_image_upload(
        file,
        owner_id=current_user.id,
        category="courses/thumbnails",
        max_bytes=settings.MAX_IMAGE_SIZE_BYTES,
    )
    return FileUploadResponse(url=url)


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CourseResponse:
    skill_result = await session.execute(select(Skill).where(Skill.id == payload.skill_id))
    skill = skill_result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    course = Course(
        skill_id=payload.skill_id,
        name=payload.name,
        thumbnail_url=payload.thumbnail_url,
        link=payload.link,
        is_active=payload.is_active,
    )
    session.add(course)
    await session.flush()
    await session.refresh(course)
    return CourseResponse(
        id=course.id,
        skill_id=course.skill_id,
        skill_name=skill.name,
        name=course.name,
        thumbnail_url=course.thumbnail_url,
        link=course.link,
        is_active=course.is_active,
        created_at=course.created_at,
    )


@router.get("/courses", response_model=CourseListResponse)
async def list_admin_courses(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    skill_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> CourseListResponse:
    query = select(Course, Skill).join(Skill, Course.skill_id == Skill.id)
    count_query = select(func.count()).select_from(Course)

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


@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CourseResponse:
    result = await session.execute(
        select(Course, Skill).join(Skill, Course.skill_id == Skill.id).where(Course.id == course_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    course, skill = row
    was_active = course.is_active

    if payload.name is not None:
        course.name = payload.name
    if payload.thumbnail_url is not None:
        if course.thumbnail_url and course.thumbnail_url != payload.thumbnail_url:
            delete_upload_if_local(course.thumbnail_url)
        course.thumbnail_url = payload.thumbnail_url
    if payload.link is not None:
        course.link = payload.link
    if payload.is_active is not None:
        if was_active and not payload.is_active:
            await ensure_can_remove_course(session, course)
        course.is_active = payload.is_active

    session.add(course)
    await session.refresh(course)
    return CourseResponse(
        id=course.id,
        skill_id=course.skill_id,
        skill_name=skill.name,
        name=course.name,
        thumbnail_url=course.thumbnail_url,
        link=course.link,
        is_active=course.is_active,
        created_at=course.created_at,
    )


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    result = await session.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if course.is_active:
        await ensure_can_remove_course(session, course)

    delete_upload_if_local(course.thumbnail_url)
    await session.delete(course)


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


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    role: UserRole | None = None,
    q: str | None = None,
    include_deleted: bool = False,
) -> AdminUserListResponse:
    filters = [User.role.in_([UserRole.freelancer, UserRole.client])]
    if not include_deleted:
        filters.append(User.is_deleted.is_(False))
    if role is not None:
        filters.append(User.role == role)
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                User.email.ilike(pattern),
                FreelancerProfile.display_name.ilike(pattern),
                ClientProfile.company_name.ilike(pattern),
            )
        )

    base = (
        select(User, FreelancerProfile, ClientProfile)
        .outerjoin(FreelancerProfile, FreelancerProfile.user_id == User.id)
        .outerjoin(ClientProfile, ClientProfile.user_id == User.id)
        .where(*filters)
    )

    total_result = await session.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = total_result.scalar_one()

    result = await session.execute(
        base.order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )

    items: list[AdminUserSummary] = []
    for user, freelancer_profile, client_profile in result.all():
        if user.role == UserRole.freelancer and freelancer_profile is not None:
            display_name = freelancer_profile.display_name
        elif user.role == UserRole.client and client_profile is not None:
            display_name = client_profile.company_name or user.email
        else:
            display_name = user.email

        items.append(
            AdminUserSummary(
                id=user.id,
                email=user.email,
                role=enum_to_str(user.role),
                display_name=display_name,
                is_banned=user.is_banned,
                is_deleted=user.is_deleted,
                ban_reason=user.ban_reason,
                created_at=user.created_at,
                deleted_at=user.deleted_at,
            )
        )

    return AdminUserListResponse(items=items, page=page, limit=limit, total=total)


@router.delete("/users/{user_id}", response_model=AdminUserDeleteResponse)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AdminUserDeleteResponse:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own account",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Admin accounts cannot be deleted from moderation",
        )

    if user.role not in (UserRole.freelancer, UserRole.client):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only freelancer or client accounts can be deleted",
        )

    deleted_at = await delete_user_for_report(session, user)
    return AdminUserDeleteResponse(
        user_id=user.id,
        role=enum_to_str(user.role),
        deleted_at=deleted_at,
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


@router.get("/reports", response_model=UserReportListResponse)
async def list_reports(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    status_filter: ReportStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> UserReportListResponse:
    query = select(UserReport)
    count_query = select(func.count()).select_from(UserReport)

    if status_filter is not None:
        query = query.where(UserReport.status == status_filter)
        count_query = count_query.where(UserReport.status == status_filter)

    total = int((await session.execute(count_query)).scalar_one())
    result = await session.execute(
        query.order_by(UserReport.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [UserReportResponse.model_validate(item) for item in result.scalars().all()]
    return UserReportListResponse(items=items, page=page, limit=limit, total=total)


@router.patch("/reports/{report_id}", response_model=UserReportResolveResponse)
async def resolve_report(
    report_id: UUID,
    payload: UserReportResolveRequest,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserReportResolveResponse:
    report, deleted_at = await resolve_user_report(
        session,
        report_id=report_id,
        admin=current_user,
        status=payload.status,
    )
    return UserReportResolveResponse(
        report=UserReportResponse.model_validate(report),
        reported_user_deleted_at=deleted_at,
    )


@router.get("/jobs", response_model=AdminJobListResponse)
async def list_all_jobs(
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    q: str | None = Query(default=None),
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> AdminJobListResponse:
    query = select(Job).join(User, Job.client_id == User.id)
    count_query = select(func.count()).select_from(Job).join(User, Job.client_id == User.id)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Job.title.ilike(pattern))
        count_query = count_query.where(Job.title.ilike(pattern))
    if status_filter is not None:
        query = query.where(Job.status == status_filter)
        count_query = count_query.where(Job.status == status_filter)

    total = int((await session.execute(count_query)).scalar_one())
    result = await session.execute(
        query.order_by(Job.posted_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    jobs = result.scalars().unique().all()

    items: list[AdminJobSummary] = []
    for job in jobs:
        counts_result = await session.execute(
            select(
                func.count(Application.id),
                func.coalesce(
                    func.sum(
                        case((Application.status == ApplicationStatus.pending, 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((Application.status == ApplicationStatus.accepted, 1), else_=0)
                    ),
                    0,
                ),
            ).where(Application.job_id == job.id)
        )
        application_count, pending_count, accepted_count = counts_result.one()
        items.append(
            AdminJobSummary(
                job=await _build_admin_job_response(session, job),
                application_count=int(application_count),
                pending_count=int(pending_count),
                accepted_count=int(accepted_count),
            )
        )

    return AdminJobListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/jobs/{job_id}/applicants", response_model=AdminJobApplicantsResponse)
async def list_job_applicants(
    job_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AdminJobApplicantsResponse:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    if job_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    applicants = await _build_admin_applicant_list(session, job_id)
    return AdminJobApplicantsResponse(job_id=job_id, applicants=applicants)
