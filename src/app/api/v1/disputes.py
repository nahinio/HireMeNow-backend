from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.engine import get_async_session
from app.models.enums import ApplicationStatus, JobStatus
from app.models.job import Application, Job
from app.models.review import Dispute
from app.models.user import FreelancerProfile, User
from app.schemas.review import DisputeCreate, DisputeResponse

router = APIRouter(prefix="/disputes", tags=["disputes"])


async def _verify_job_party(
    session: AsyncSession, job: Job, user: User
) -> None:
    if job.client_id == user.id:
        return

    profile_result = await session.execute(
        select(FreelancerProfile).where(FreelancerProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a party to this job",
        )

    application_result = await session.execute(
        select(Application).where(
            Application.job_id == job.id,
            Application.freelancer_id == profile.id,
            Application.status.in_(
                [ApplicationStatus.pending, ApplicationStatus.accepted]
            ),
        )
    )
    if application_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a party to this job",
        )


@router.post("", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def raise_dispute(
    payload: DisputeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Dispute:
    job_result = await session.execute(select(Job).where(Job.id == payload.job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await _verify_job_party(session, job, current_user)

    existing_result = await session.execute(
        select(Dispute).where(Dispute.job_id == payload.job_id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute already exists for this job",
        )

    dispute = Dispute(
        job_id=payload.job_id,
        raised_by=current_user.id,
        description=payload.description,
    )
    session.add(dispute)

    job.status = JobStatus.disputed
    session.add(job)

    await session.flush()
    await session.refresh(dispute)
    return dispute
