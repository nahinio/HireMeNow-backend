from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ApplicationStatus, JobStatus, UserRole
from app.models.job import Application, Job
from app.models.user import ClientProfile, FreelancerProfile, TokenBlocklist, User
from app.services.uploads import delete_upload_if_local


async def _ensure_not_deleted(user: User) -> None:
    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already deleted",
        )


async def _block_user_tokens(session: AsyncSession, user_id: UUID) -> None:
    blocklist_result = await session.execute(
        select(TokenBlocklist).where(TokenBlocklist.user_id == user_id)
    )
    if blocklist_result.scalar_one_or_none() is None:
        session.add(TokenBlocklist(user_id=user_id))


async def soft_delete_freelancer(
    session: AsyncSession, user: User
) -> datetime:
    await _ensure_not_deleted(user)
    if user.role != UserRole.freelancer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Freelancer account required",
        )

    profile_result = await session.execute(
        select(FreelancerProfile).where(FreelancerProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one()

    await session.execute(
        update(Application)
        .where(
            Application.freelancer_id == profile.id,
            Application.status == ApplicationStatus.pending,
        )
        .values(status=ApplicationStatus.canceled)
    )

    profile.available_for_work = False
    profile.updated_at = datetime.now(timezone.utc)
    delete_upload_if_local(profile.profile_picture_url)
    delete_upload_if_local(profile.resume_url)
    session.add(profile)

    deleted_at = datetime.now(timezone.utc)
    user.is_deleted = True
    user.deleted_at = deleted_at
    session.add(user)
    await _block_user_tokens(session, user.id)
    return deleted_at


async def soft_delete_client(session: AsyncSession, user: User) -> datetime:
    await _ensure_not_deleted(user)
    if user.role != UserRole.client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client account required",
        )

    profile_result = await session.execute(
        select(ClientProfile).where(ClientProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one()

    await session.execute(
        update(Job)
        .where(Job.client_id == user.id, Job.status == JobStatus.open)
        .values(status=JobStatus.closed, updated_at=datetime.now(timezone.utc))
    )

    await session.execute(
        update(Application)
        .where(
            Application.job_id.in_(select(Job.id).where(Job.client_id == user.id)),
            Application.status == ApplicationStatus.pending,
        )
        .values(status=ApplicationStatus.canceled)
    )

    delete_upload_if_local(profile.profile_picture_url)
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)

    deleted_at = datetime.now(timezone.utc)
    user.is_deleted = True
    user.deleted_at = deleted_at
    session.add(user)
    await _block_user_tokens(session, user.id)
    return deleted_at


async def delete_user_for_report(session: AsyncSession, user: User) -> datetime:
    if user.is_deleted:
        return user.deleted_at or datetime.now(timezone.utc)

    if user.role == UserRole.freelancer:
        profile_result = await session.execute(
            select(FreelancerProfile).where(FreelancerProfile.user_id == user.id)
        )
        profile = profile_result.scalar_one()
        await session.execute(
            update(Application)
            .where(
                Application.freelancer_id == profile.id,
                Application.status.in_(
                    [ApplicationStatus.pending, ApplicationStatus.accepted]
                ),
            )
            .values(status=ApplicationStatus.canceled)
        )
        return await soft_delete_freelancer(session, user)

    if user.role == UserRole.client:
        await session.execute(
            update(Job)
            .where(
                Job.client_id == user.id,
                Job.status != JobStatus.completed,
            )
            .values(status=JobStatus.closed, updated_at=datetime.now(timezone.utc))
        )
        await session.execute(
            update(Application)
            .where(
                Application.job_id.in_(select(Job.id).where(Job.client_id == user.id)),
                Application.status.in_(
                    [ApplicationStatus.pending, ApplicationStatus.accepted]
                ),
            )
            .values(status=ApplicationStatus.canceled)
        )
        return await soft_delete_client(session, user)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Only freelancer or client accounts can be removed via reports",
    )
