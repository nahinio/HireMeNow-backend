import pytest
from pydantic import ValidationError

from app.schemas.skill import BulkQuizOptionCreate, BulkQuizQuestionCreate, SkillWithQuizCreate


def _four_options(correct_index: int = 0):
    return [
        BulkQuizOptionCreate(body=f"Option {i}", is_correct=(i == correct_index))
        for i in range(4)
    ]


def test_skill_with_quiz_requires_unique_positions():
    with pytest.raises(ValidationError):
        SkillWithQuizCreate(
            name="Python",
            questions=[
                BulkQuizQuestionCreate(body="Q1", position=1, options=_four_options()),
                BulkQuizQuestionCreate(body="Q2", position=1, options=_four_options(1)),
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
                        BulkQuizOptionCreate(body="C"),
                        BulkQuizOptionCreate(body="D"),
                    ],
                ),
            ],
        )


def test_skill_with_quiz_requires_four_options():
    with pytest.raises(ValidationError):
        BulkQuizQuestionCreate(
            body="Q1",
            position=1,
            options=[
                BulkQuizOptionCreate(body="A", is_correct=True),
                BulkQuizOptionCreate(body="B"),
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
                options=_four_options(1),
            ),
        ],
    )
    assert payload.name == "Python"
    assert len(payload.questions) == 1
    assert len(payload.questions[0].options) == 4
