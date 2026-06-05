"""Remove disputes feature

Revision ID: 005
Revises: 004
Create Date: 2026-06-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("disputes")
    op.execute("DROP TYPE IF EXISTS dispute_status")

    op.execute("UPDATE jobs SET status = 'open' WHERE status = 'disputed'")
    op.execute("ALTER TYPE job_status RENAME TO job_status_old")
    op.execute(
        "CREATE TYPE job_status AS ENUM "
        "('open', 'pending_confirmation', 'completed', 'closed')"
    )
    op.execute("ALTER TABLE jobs ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN status TYPE job_status "
        "USING status::text::job_status"
    )
    op.execute("ALTER TABLE jobs ALTER COLUMN status SET DEFAULT 'open'::job_status")
    op.execute("DROP TYPE job_status_old")


def downgrade() -> None:
    op.execute("ALTER TYPE job_status RENAME TO job_status_old")
    op.execute(
        "CREATE TYPE job_status AS ENUM "
        "('open', 'pending_confirmation', 'completed', 'closed', 'disputed')"
    )
    op.execute("ALTER TABLE jobs ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN status TYPE job_status "
        "USING status::text::job_status"
    )
    op.execute("ALTER TABLE jobs ALTER COLUMN status SET DEFAULT 'open'::job_status")
    op.execute("DROP TYPE job_status_old")

    dispute_status = postgresql.ENUM(
        "open", "under_review", "resolved", "closed", name="dispute_status"
    )
    dispute_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "disputes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("raised_by", sa.Uuid(), nullable=False),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", dispute_status, server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["raised_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
