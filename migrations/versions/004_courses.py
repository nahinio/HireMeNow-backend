"""Courses for skills

Revision ID: 004
Revises: 003
Create Date: 2026-06-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_courses_skill_id", "courses", ["skill_id"])


def downgrade() -> None:
    op.drop_index("ix_courses_skill_id", table_name="courses")
    op.drop_table("courses")
