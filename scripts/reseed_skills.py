"""Upsert default catalog skills (with quizzes) without removing other skills in the database."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete, func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.db.engine import async_session_maker  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.skill import (  # noqa: E402
    AnswerOption,
    Question,
    Quiz,
    QuizAttempt,
    Skill,
    SkillBadge,
)
from app.models.job import JobRequiredSkill  # noqa: E402
from app.models.user import User  # noqa: E402
from skills_quiz_data import SKILLS  # noqa: E402

ADMIN_EMAIL = "admin@hiremenow.com"

COURSE_LINKS = {
    "HTML-CSS": "https://www.youtube.com/watch?v=G3e-cpL7ofc",
    "Vanilla Javascript": "https://www.youtube.com/watch?v=PkZNo7MFNFg",
    "C++": "https://www.youtube.com/watch?v=vLnPwxZdW4Y",
    "FastAPI (Python)": "https://www.youtube.com/watch?v=0sOvCWHmTDE",
    "ReactJS": "https://www.youtube.com/watch?v=Tn6PIPBU_JU",
    "Agentic AI": "https://www.youtube.com/watch?v=sal78ACtGTc",
    "LLM Basics": "https://www.youtube.com/watch?v=5sLYAQS9sEQ",
}

async def _delete_quiz_questions(session, quiz_id) -> None:
    question_ids = [
        row[0]
        for row in (
            await session.execute(select(Question.id).where(Question.quiz_id == quiz_id))
        ).all()
    ]
    if not question_ids:
        return
    await session.execute(
        delete(AnswerOption).where(AnswerOption.question_id.in_(question_ids))
    )
    await session.execute(delete(Question).where(Question.quiz_id == quiz_id))


async def wipe_all_skills(session) -> int:
    """Destructive: removes every skill. Use only with --wipe-all."""
    question_ids = [row[0] for row in (await session.execute(select(Question.id))).all()]
    if question_ids:
        await session.execute(
            delete(AnswerOption).where(AnswerOption.question_id.in_(question_ids))
        )

    await session.execute(delete(Question))
    await session.execute(delete(QuizAttempt))
    await session.execute(delete(SkillBadge))
    await session.execute(delete(JobRequiredSkill))
    await session.execute(delete(Course))
    await session.execute(delete(Quiz))

    skill_count = len((await session.execute(select(Skill.id))).all())
    await session.execute(delete(Skill))
    return skill_count


async def upsert_catalog_skill(session, admin_id, skill_data) -> str:
    result = await session.execute(
        select(Skill).where(func.lower(Skill.name) == skill_data["name"].lower())
    )
    skill = result.scalar_one_or_none()
    action = "updated" if skill else "created"

    if skill is None:
        skill = Skill(
            name=skill_data["name"],
            description=skill_data["description"],
            is_active=True,
            created_by=admin_id,
        )
        session.add(skill)
        await session.flush()
    else:
        skill.description = skill_data["description"]
        skill.is_active = True
        session.add(skill)
        await session.flush()

    quiz_result = await session.execute(select(Quiz).where(Quiz.skill_id == skill.id))
    quiz = quiz_result.scalar_one_or_none()
    if quiz is None:
        quiz = Quiz(
            skill_id=skill.id,
            pass_threshold=skill_data["pass_threshold"],
            published=True,
        )
        session.add(quiz)
        await session.flush()
    else:
        await _delete_quiz_questions(session, quiz.id)
        quiz.pass_threshold = skill_data["pass_threshold"]
        quiz.published = True
        session.add(quiz)
        await session.flush()

    for position, question_data in enumerate(skill_data["questions"], start=1):
        question = Question(
            quiz_id=quiz.id,
            body=question_data["body"],
            position=position,
        )
        session.add(question)
        await session.flush()

        for option_data in question_data["options"]:
            session.add(
                AnswerOption(
                    question_id=question.id,
                    body=option_data["body"],
                    is_correct=option_data["is_correct"],
                )
            )

    course_link = COURSE_LINKS.get(
        skill_data["name"],
        "https://www.youtube.com/watch?v=Tn6PIPBU_JU",
    )
    course_result = await session.execute(
        select(Course).where(Course.skill_id == skill.id).limit(1)
    )
    course = course_result.scalar_one_or_none()
    if course is None:
        session.add(
            Course(
                skill_id=skill.id,
                name=f"{skill_data['name']} — Recommended course",
                link=course_link,
                thumbnail_url=None,
                is_active=True,
            )
        )
    else:
        course.name = f"{skill_data['name']} — Recommended course"
        course.link = course_link
        course.is_active = True
        session.add(course)

    return action


async def main(*, wipe_all: bool) -> None:
    async with async_session_maker() as session:
        admin = (
            await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        if admin is None:
            raise SystemExit(f"Admin user not found: {ADMIN_EMAIL}")

        removed = 0
        if wipe_all:
            removed = await wipe_all_skills(session)

        created = 0
        updated = 0
        for skill_data in SKILLS:
            action = await upsert_catalog_skill(session, admin.id, skill_data)
            if action == "created":
                created += 1
            else:
                updated += 1

        await session.commit()

    total_questions = sum(len(s["questions"]) for s in SKILLS)
    print("Catalog skills reseeded successfully.")
    if wipe_all:
        print(f"  Wiped:   {removed} skill(s) (--wipe-all)")
    else:
        print("  Other skills in the database were left unchanged.")
    print(f"  Catalog: {len(SKILLS)} skills ({created} created, {updated} updated)")
    print(f"  Questions per catalog skill: {total_questions // len(SKILLS)} avg")
    for skill in SKILLS:
        print(f"    - {skill['name']} ({len(skill['questions'])} questions)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upsert catalog skills with quizzes. Legacy skills without quizzes are preserved."
    )
    parser.add_argument(
        "--wipe-all",
        action="store_true",
        help="Delete ALL skills first (destructive). Default: only upsert catalog skills.",
    )
    args = parser.parse_args()
    asyncio.run(main(wipe_all=args.wipe_all))
