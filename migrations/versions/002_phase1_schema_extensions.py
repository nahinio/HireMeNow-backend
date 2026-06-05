"""Phase 1 schema extensions

Revision ID: 002
Revises: 001
Create Date: 2026-06-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

report_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    name="report_status",
    create_type=False,
)


def _create_enum(enum_name: str, values: tuple[str, ...]) -> None:
    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {enum_name} AS ENUM ({values_sql});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def upgrade() -> None:
    _create_enum("report_status", ("pending", "approved", "rejected"))

    op.add_column(
        "skills",
        sa.Column("description", sa.Text(), server_default="", nullable=False),
    )

    op.add_column(
        "users",
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "freelancer_profiles",
        sa.Column("profile_picture_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "freelancer_profiles",
        sa.Column("resume_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "freelancer_profiles",
        sa.Column("linkedin_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "freelancer_profiles",
        sa.Column("contact_email", sa.Text(), nullable=True),
    )
    op.add_column(
        "freelancer_profiles",
        sa.Column("github_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "freelancer_profiles",
        sa.Column("portfolio_url", sa.Text(), nullable=True),
    )

    op.add_column(
        "client_profiles",
        sa.Column("bio", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "client_profiles",
        sa.Column("profile_picture_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "client_profiles",
        sa.Column("company_link", sa.Text(), nullable=True),
    )

    op.add_column("jobs", sa.Column("thumbnail_url", sa.Text(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column(
            "requirements_education",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "requirements_experience",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "requirements_additional",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("responsibilities", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column("about_role", sa.Text(), server_default="", nullable=False),
    )
    op.add_column("jobs", sa.Column("salary_amount", sa.Numeric(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column(
            "salary_negotiable",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("other_benefits", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column("company_name", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column("company_description", sa.Text(), server_default="", nullable=False),
    )

    op.create_table(
        "user_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("reported_user_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", report_status, server_default="pending", nullable=False),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_reports_reported_user_status",
        "user_reports",
        ["reported_user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_reports_reported_user_status", table_name="user_reports")
    op.drop_table("user_reports")

    op.drop_column("jobs", "company_description")
    op.drop_column("jobs", "company_name")
    op.drop_column("jobs", "other_benefits")
    op.drop_column("jobs", "salary_negotiable")
    op.drop_column("jobs", "salary_amount")
    op.drop_column("jobs", "about_role")
    op.drop_column("jobs", "responsibilities")
    op.drop_column("jobs", "requirements_additional")
    op.drop_column("jobs", "requirements_experience")
    op.drop_column("jobs", "requirements_education")
    op.drop_column("jobs", "thumbnail_url")

    op.drop_column("client_profiles", "company_link")
    op.drop_column("client_profiles", "profile_picture_url")
    op.drop_column("client_profiles", "bio")

    op.drop_column("freelancer_profiles", "portfolio_url")
    op.drop_column("freelancer_profiles", "github_url")
    op.drop_column("freelancer_profiles", "contact_email")
    op.drop_column("freelancer_profiles", "linkedin_url")
    op.drop_column("freelancer_profiles", "resume_url")
    op.drop_column("freelancer_profiles", "profile_picture_url")

    op.drop_column("users", "deleted_at")
    op.drop_column("users", "is_deleted")

    op.drop_column("skills", "description")

    op.execute("DROP TYPE IF EXISTS report_status")
