import pytest
from pydantic import ValidationError

from app.schemas.skill import BulkQuizOptionCreate, BulkQuizQuestionCreate, SkillWithQuizCreate


def test_skill_with_quiz_requires_unique_positions():
    with pytest.raises(ValidationError):
        SkillWithQuizCreate(
            name="Python",
            questions=[
                BulkQuizQuestionCreate(
                    body="Q1",
                    position=1,
                    options=[
                        BulkQuizOptionCreate(body="A", is_correct=True),
                        BulkQuizOptionCreate(body="B"),
                    ],
                ),
                BulkQuizQuestionCreate(
                    body="Q2",
                    position=1,
                    options=[
                        BulkQuizOptionCreate(body="A", is_correct=True),
                        BulkQuizOptionCreate(body="B"),
                    ],
                ),
            ],
        )


def test_skill_with_quiz_requires_one_correct_option():
    with pytest.raises(ValidationError):
        SkillWithQuizCreate(
            name="Python",
            questions=[
                BulkQuizQuestionCreate(
                    body="Q1",
                    position=1,
                    options=[
                        BulkQuizOptionCreate(body="A"),
                        BulkQuizOptionCreate(body="B"),
                    ],
                ),
            ],
        )


def test_skill_with_quiz_accepts_valid_payload():
    payload = SkillWithQuizCreate(
        name="Python",
        description="Python programming",
        published=True,
        questions=[
            BulkQuizQuestionCreate(
                body="What is 2+2?",
                position=1,
                options=[
                    BulkQuizOptionCreate(body="3"),
                    BulkQuizOptionCreate(body="4", is_correct=True),
                ],
            ),
        ],
    )
    assert payload.name == "Python"
    assert len(payload.questions) == 1
