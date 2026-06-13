"""Add is_system flag and nullable sender_id on messages

Revision ID: 008
Revises: 007
Create Date: 2026-06-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("messages", "sender_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.alter_column("messages", "sender_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("messages", "is_system")
