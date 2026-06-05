import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Numeric, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.columns import timestamptz
from app.models.db_types import quiz_result_enum
from app.models.enums import QuizResult
from app.models.user import utcnow


class Skill(SQLModel, table=True):
    __tablename__ = "skills"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(sa_column=Column(Text, unique=True, nullable=False))
    description: str = Field(
        default="", sa_column=Column(Text, nullable=False, server_default="")
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
    created_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)


class Quiz(SQLModel, table=True):
    __tablename__ = "quizzes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    skill_id: uuid.UUID = Field(foreign_key="skills.id", unique=True, nullable=False)
    pass_threshold: int = Field(nullable=False)
    published: bool = Field(default=False)


class Question(SQLModel, table=True):
    __tablename__ = "quiz_questions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: uuid.UUID = Field(foreign_key="quizzes.id", nullable=False)
    body: str = Field(sa_column=Column(Text, nullable=False))
    position: int = Field(nullable=False)


class AnswerOption(SQLModel, table=True):
    __tablename__ = "answer_options"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    question_id: uuid.UUID = Field(foreign_key="quiz_questions.id", nullable=False)
    body: str = Field(sa_column=Column(Text, nullable=False))
    is_correct: bool = Field(default=False)


class QuizAttempt(SQLModel, table=True):
    __tablename__ = "quiz_attempts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: uuid.UUID = Field(foreign_key="quizzes.id", nullable=False)
    profile_id: uuid.UUID = Field(foreign_key="freelancer_profiles.id", nullable=False)
    score: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    result: QuizResult = Field(sa_column=Column(quiz_result_enum, nullable=False))
    attempted_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )


class SkillBadge(SQLModel, table=True):
    __tablename__ = "skill_badges"
    __table_args__ = (UniqueConstraint("profile_id", "skill_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    profile_id: uuid.UUID = Field(foreign_key="freelancer_profiles.id", nullable=False)
    skill_id: uuid.UUID = Field(foreign_key="skills.id", nullable=False)
    score: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    earned_at: datetime = Field(
        default_factory=utcnow, sa_column=Column(timestamptz, nullable=False)
    )
