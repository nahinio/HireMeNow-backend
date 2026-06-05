from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReportStatus, UserRole
from app.models.report import UserReport
from app.models.user import User
from app.services.profile import delete_user_for_report


async def create_user_report(
    session: AsyncSession,
    *,
    reporter: User,
    reported_user_id: UUID,
    description: str,
) -> UserReport:
    if reporter.role not in (UserRole.freelancer, UserRole.client):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only freelancers and clients can submit reports",
        )
    if reporter.id == reported_user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot report yourself",
        )

    reported_result = await session.execute(
        select(User).where(User.id == reported_user_id)
    )
    reported_user = reported_result.scalar_one_or_none()
    if reported_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reported user not found",
        )
    if reported_user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Admin accounts cannot be reported",
        )
    if reported_user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reported account is no longer active",
        )
    if reporter.role == reported_user.role:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Freelancers can only report clients and clients can only report freelancers",
        )

    pending_result = await session.execute(
        select(UserReport).where(
            UserReport.reporter_id == reporter.id,
            UserReport.reported_user_id == reported_user_id,
            UserReport.status == ReportStatus.pending,
        )
    )
    if pending_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending report already exists for this user",
        )

    report = UserReport(
        reporter_id=reporter.id,
        reported_user_id=reported_user_id,
        description=description,
    )
    session.add(report)
    await session.flush()
    await session.refresh(report)
    return report


async def resolve_user_report(
    session: AsyncSession,
    *,
    report_id: UUID,
    admin: User,
    status: ReportStatus,
) -> tuple[UserReport, datetime | None]:
    if status == ReportStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resolution status must be approved or rejected",
        )

    result = await session.execute(select(UserReport).where(UserReport.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    if report.status != ReportStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report has already been resolved",
        )

    report.status = status
    report.resolved_by = admin.id
    report.resolved_at = datetime.now(timezone.utc)
    session.add(report)

    deleted_at: datetime | None = None
    if status == ReportStatus.approved:
        reported_result = await session.execute(
            select(User).where(User.id == report.reported_user_id)
        )
        reported_user = reported_result.scalar_one()
        deleted_at = await delete_user_for_report(session, reported_user)

    await session.refresh(report)
    return report, deleted_at
