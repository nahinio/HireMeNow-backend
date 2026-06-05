from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.engine import get_async_session
from app.models.enums import ApplicationStatus, JobStatus, UserRole
from app.models.job import Application, Job
from app.models.review import Review
from app.models.user import FreelancerProfile, User
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.reviews import update_profile_ratings_for_user

router = APIRouter(tags=["reviews"])


async def _get_accepted_freelancer_user_id(
    session: AsyncSession, job_id: UUID
) -> UUID | None:
    result = await session.execute(
        select(FreelancerProfile.user_id)
        .join(Application, Application.freelancer_id == FreelancerProfile.id)
        .where(
            Application.job_id == job_id,
            Application.status == ApplicationStatus.accepted,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_job_parties(session: AsyncSession, job: Job) -> tuple[UUID, UUID]:
    client_id = job.client_id
    freelancer_user_id = await _get_accepted_freelancer_user_id(session, job.id)
    if freelancer_user_id is None:
        app_result = await session.execute(
            select(FreelancerProfile.user_id)
            .join(Application, Application.freelancer_id == FreelancerProfile.id)
            .where(Application.job_id == job.id)
            .limit(1)
        )
        freelancer_user_id = app_result.scalar_one_or_none()
    if freelancer_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No freelancer associated with this job",
        )
    return client_id, freelancer_user_id


@router.post("/jobs/{job_id}/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_review(
    job_id: UUID,
    payload: ReviewCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Review:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.pending_confirmation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reviews can only be submitted during pending_confirmation",
        )

    client_id, freelancer_user_id = await _get_job_parties(session, job)
    if current_user.id not in (client_id, freelancer_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a party to this job",
        )

    reviewee_id = (
        freelancer_user_id if current_user.id == client_id else client_id
    )

    existing_result = await session.execute(
        select(Review).where(
            Review.job_id == job_id,
            Review.reviewer_id == current_user.id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review already submitted",
        )

    review = Review(
        job_id=job_id,
        reviewer_id=current_user.id,
        reviewee_id=reviewee_id,
        rating=payload.rating,
        body=payload.body,
        is_published=False,
    )
    session.add(review)
    await session.flush()

    client_review_result = await session.execute(
        select(Review).where(
            Review.job_id == job_id,
            Review.reviewer_id == client_id,
        )
    )
    freelancer_review_result = await session.execute(
        select(Review).where(
            Review.job_id == job_id,
            Review.reviewer_id == freelancer_user_id,
        )
    )
    if (
        client_review_result.scalar_one_or_none() is not None
        and freelancer_review_result.scalar_one_or_none() is not None
    ):
        now = datetime.now(timezone.utc)
        reviews_result = await session.execute(
            select(Review).where(Review.job_id == job_id)
        )
        for existing_review in reviews_result.scalars().all():
            existing_review.is_published = True
            existing_review.published_at = now
            session.add(existing_review)

        await update_profile_ratings_for_user(session, client_id)
        await update_profile_ratings_for_user(session, freelancer_user_id)

        job.status = JobStatus.completed
        job.updated_at = now
        session.add(job)

    await session.refresh(review)
    return review


@router.get("/users/{user_id}/reviews", response_model=list[ReviewResponse])
async def list_user_reviews(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[Review]:
    result = await session.execute(
        select(Review)
        .where(
            Review.reviewee_id == user_id,
            Review.is_published.is_(True),
            Review.is_deleted.is_(False),
        )
        .order_by(Review.published_at.desc())
    )
    return list(result.scalars().all())
