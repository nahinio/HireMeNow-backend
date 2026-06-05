"""Add filled job status for selected candidates

Revision ID: 006
Revises: 005
Create Date: 2026-06-05

"""

from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'filled'")


def downgrade() -> None:
    op.execute("UPDATE jobs SET status = 'open' WHERE status = 'filled'")
