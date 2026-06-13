from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.job import JobRequiredSkill
from app.models.skill import AnswerOption, Question, Quiz, QuizAttempt, Skill, SkillBadge
from app.schemas.skill import (
    AdminSkillDetailResponse,
    AdminSkillListResponse,
    AdminSkillSummary,
    AnswerOptionResponse,
    QuizResponse,
    SkillQuizReplace,
    SkillResponse,
    SkillUpdate,
    SkillWithQuizCreate,
    SkillWithQuizQuestionResponse,
    SkillWithQuizResponse,
)
from app.services.courses import ensure_skill_has_minimum_courses
from app.services.uploads import delete_upload_if_local


async def _get_skill_or_404(session: AsyncSession, skill_id: UUID) -> Skill:
    result = await session.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


async def _load_skill_quiz_response(
    session: AsyncSession,
    skill: Skill,
) -> SkillWithQuizResponse:
    quiz_result = await session.execute(select(Quiz).where(Quiz.skill_id == skill.id))
    quiz = quiz_result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found for this skill",
        )

    questions_result = await session.execute(
        select(Question)
        .where(Question.quiz_id == quiz.id)
        .order_by(Question.position.asc())
    )
    questions = questions_result.scalars().all()

    question_records = []
    for question in questions:
        options_result = await session.execute(
            select(AnswerOption)
            .where(AnswerOption.question_id == question.id)
            .order_by(AnswerOption.id.asc())
        )
        question_records.append((question, options_result.scalars().all()))

    return SkillWithQuizResponse.from_records(
        skill=skill,
        quiz=quiz,
        question_records=question_records,
    )


async def _delete_quiz_questions(session: AsyncSession, quiz_id: UUID) -> None:
    question_ids_result = await session.execute(
        select(Question.id).where(Question.quiz_id == quiz_id)
    )
    question_ids = [row[0] for row in question_ids_result.all()]
    if not question_ids:
        return

    await session.execute(
        delete(AnswerOption).where(AnswerOption.question_id.in_(question_ids))
    )
    await session.execute(delete(Question).where(Question.quiz_id == quiz_id))


async def _create_quiz_questions(
    session: AsyncSession,
    quiz: Quiz,
    questions_payload,
) -> list[tuple[Question, list[AnswerOption]]]:
    question_records = []
    for question_payload in sorted(questions_payload, key=lambda item: item.position):
        question = Question(
            quiz_id=quiz.id,
            body=question_payload.body,
            position=question_payload.position,
        )
        session.add(question)
        await session.flush()

        option_records = []
        for option_payload in question_payload.options:
            option = AnswerOption(
                question_id=question.id,
                body=option_payload.body,
                is_correct=option_payload.is_correct,
            )
            session.add(option)
            await session.flush()
            option_records.append(option)

        question_records.append((question, option_records))
    return question_records


async def list_admin_skills(
    session: AsyncSession,
    *,
    page: int,
    limit: int,
) -> AdminSkillListResponse:
    offset = (page - 1) * limit

    count_result = await session.execute(select(func.count()).select_from(Skill))
    total = int(count_result.scalar_one())

    question_count_sq = (
        select(func.count(Question.id))
        .where(Question.quiz_id == Quiz.id)
        .correlate(Quiz)
        .scalar_subquery()
    )

    result = await session.execute(
        select(
            Skill,
            Quiz,
            func.coalesce(question_count_sq, 0).label("question_count"),
        )
        .outerjoin(Quiz, Quiz.skill_id == Skill.id)
        .order_by(Skill.name.asc())
        .offset(offset)
        .limit(limit)
    )

    items: list[AdminSkillSummary] = []
    for skill, quiz, question_count in result.all():
        items.append(
            AdminSkillSummary(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                is_active=skill.is_active,
                quiz_id=quiz.id if quiz else None,
                pass_threshold=quiz.pass_threshold if quiz else None,
                published=quiz.published if quiz else None,
                question_count=int(question_count or 0),
            )
        )

    return AdminSkillListResponse(items=items, page=page, limit=limit, total=total)


async def get_skill_detail_admin(
    session: AsyncSession,
    skill_id: UUID,
) -> AdminSkillDetailResponse:
    skill = await _get_skill_or_404(session, skill_id)
    quiz_result = await session.execute(select(Quiz).where(Quiz.skill_id == skill.id))
    quiz = quiz_result.scalar_one_or_none()

    if quiz is None:
        return AdminSkillDetailResponse(skill=SkillResponse.model_validate(skill))

    questions_result = await session.execute(
        select(Question)
        .where(Question.quiz_id == quiz.id)
        .order_by(Question.position.asc())
    )
    questions = questions_result.scalars().all()

    question_ids = [question.id for question in questions]
    options_by_question: dict = {}
    if question_ids:
        options_result = await session.execute(
            select(AnswerOption)
            .where(AnswerOption.question_id.in_(question_ids))
            .order_by(AnswerOption.id.asc())
        )
        for option in options_result.scalars().all():
            options_by_question.setdefault(option.question_id, []).append(option)

    question_items = []
    for question in questions:
        options = options_by_question.get(question.id, [])
        question_items.append(
            SkillWithQuizQuestionResponse(
                id=question.id,
                body=question.body,
                position=question.position,
                options=[AnswerOptionResponse.model_validate(o) for o in options],
            )
        )

    return AdminSkillDetailResponse(
        skill=SkillResponse.model_validate(skill),
        quiz=QuizResponse(
            id=quiz.id,
            skill_id=quiz.skill_id,
            skill_name=skill.name,
            pass_threshold=quiz.pass_threshold,
            published=quiz.published,
        ),
        questions=question_items,
    )


async def get_skill_with_quiz(
    session: AsyncSession,
    skill_id: UUID,
) -> SkillWithQuizResponse:
    skill = await _get_skill_or_404(session, skill_id)
    return await _load_skill_quiz_response(session, skill)


async def update_skill(
    session: AsyncSession,
    skill_id: UUID,
    payload: SkillUpdate,
) -> SkillResponse:
    skill = await _get_skill_or_404(session, skill_id)

    if payload.name is not None and payload.name.lower() != skill.name.lower():
        existing = await session.execute(
            select(Skill).where(
                func.lower(Skill.name) == payload.name.lower(),
                Skill.id != skill_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Skill name already exists",
            )
        skill.name = payload.name

    if payload.description is not None:
        skill.description = payload.description
    if payload.is_active is not None:
        skill.is_active = payload.is_active

    session.add(skill)
    await session.flush()
    await session.refresh(skill)
    return SkillResponse.model_validate(skill)


async def replace_skill_quiz(
    session: AsyncSession,
    skill_id: UUID,
    payload: SkillQuizReplace,
) -> SkillWithQuizResponse:
    skill = await _get_skill_or_404(session, skill_id)

    quiz_result = await session.execute(select(Quiz).where(Quiz.skill_id == skill_id))
    quiz = quiz_result.scalar_one_or_none()
    if quiz is None:
        quiz = Quiz(
            skill_id=skill.id,
            pass_threshold=payload.pass_threshold,
            published=payload.published,
        )
        session.add(quiz)
        await session.flush()
    else:
        if payload.published and not quiz.published:
            await ensure_skill_has_minimum_courses(session, skill.id)
        quiz.pass_threshold = payload.pass_threshold
        quiz.published = payload.published
        session.add(quiz)
        await session.flush()
        await _delete_quiz_questions(session, quiz.id)

    question_records = await _create_quiz_questions(session, quiz, payload.questions)

    await session.refresh(skill)
    await session.refresh(quiz)

    return SkillWithQuizResponse.from_records(
        skill=skill,
        quiz=quiz,
        question_records=question_records,
    )


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

    question_records = await _create_quiz_questions(session, quiz, payload.questions)

    await session.refresh(skill)
    await session.refresh(quiz)

    return SkillWithQuizResponse.from_records(
        skill=skill,
        quiz=quiz,
        question_records=question_records,
    )


async def delete_skill(session: AsyncSession, skill_id: UUID) -> None:
    skill = await _get_skill_or_404(session, skill_id)

    quiz_result = await session.execute(select(Quiz).where(Quiz.skill_id == skill_id))
    quiz = quiz_result.scalar_one_or_none()
    if quiz is not None:
        await _delete_quiz_questions(session, quiz.id)
        await session.execute(
            delete(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id)
        )
        await session.delete(quiz)

    await session.execute(delete(SkillBadge).where(SkillBadge.skill_id == skill_id))
    await session.execute(
        delete(JobRequiredSkill).where(JobRequiredSkill.skill_id == skill_id)
    )

    courses_result = await session.execute(
        select(Course).where(Course.skill_id == skill_id)
    )
    for course in courses_result.scalars().all():
        delete_upload_if_local(course.thumbnail_url)
        await session.delete(course)

    await session.delete(skill)
