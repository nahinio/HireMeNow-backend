"""Add unique quiz question positions

Revision ID: 007
Revises: 006
Create Date: 2026-06-06

"""

from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_quiz_questions_quiz_position",
        "quiz_questions",
        ["quiz_id", "position"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_quiz_questions_quiz_position", table_name="quiz_questions")
