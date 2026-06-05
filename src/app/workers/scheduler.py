import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import async_session_maker
from app.models.enums import ApplicationStatus, JobStatus
from app.models.job import Application, Job
from app.models.messaging import CompletionSignal
from app.models.review import Review, ReviewReminder
from app.models.user import FreelancerProfile
from app.services.reviews import update_profile_ratings_for_user

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _get_pending_jobs_past_threshold(
    session: AsyncSession, hours: int
) -> list[tuple[UUID, datetime]]:
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await session.execute(
        select(CompletionSignal.job_id, func.max(CompletionSignal.signalled_at))
        .group_by(CompletionSignal.job_id)
        .having(
            func.count(CompletionSignal.id) == 2,
            func.max(CompletionSignal.signalled_at) <= threshold,
        )
    )
    qualifying: list[tuple[UUID, datetime]] = []
    for job_id, max_signalled_at in result.all():
        job_result = await session.execute(
            select(Job).where(
                Job.id == job_id,
                Job.status == JobStatus.pending_confirmation,
            )
        )
        if job_result.scalar_one_or_none() is not None:
            qualifying.append((job_id, max_signalled_at))
    return qualifying


async def _get_job_party_user_ids(
    session: AsyncSession, job_id: UUID
) -> tuple[UUID, UUID]:
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one()
    client_id = job.client_id

    freelancer_result = await session.execute(
        select(FreelancerProfile.user_id)
        .join(Application, Application.freelancer_id == FreelancerProfile.id)
        .where(Application.job_id == job_id)
        .limit(1)
    )
    freelancer_id = freelancer_result.scalar_one()
    return client_id, freelancer_id


async def send_review_reminders() -> None:
    async with async_session_maker() as session:
        try:
            jobs = await _get_pending_jobs_past_threshold(session, hours=48)
            for job_id, _ in jobs:
                client_id, freelancer_id = await _get_job_party_user_ids(session, job_id)
                for user_id in (client_id, freelancer_id):
                    review_result = await session.execute(
                        select(Review).where(
                            Review.job_id == job_id,
                            Review.reviewer_id == user_id,
                        )
                    )
                    if review_result.scalar_one_or_none() is not None:
                        continue

                    reminder_result = await session.execute(
                        select(ReviewReminder).where(
                            ReviewReminder.job_id == job_id,
                            ReviewReminder.user_id == user_id,
                            ReviewReminder.reminder_type == "48h",
                        )
                    )
                    if reminder_result.scalar_one_or_none() is not None:
                        continue

                    logger.info(
                        "48h review reminder: job_id=%s user_id=%s",
                        job_id,
                        user_id,
                    )
                    session.add(
                        ReviewReminder(
                            job_id=job_id,
                            user_id=user_id,
                            reminder_type="48h",
                        )
                    )
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def force_close_stale_jobs() -> None:
    async with async_session_maker() as session:
        try:
            jobs = await _get_pending_jobs_past_threshold(session, hours=24 * 7)
            now = datetime.now(timezone.utc)

            for job_id, _ in jobs:
                client_id, freelancer_id = await _get_job_party_user_ids(session, job_id)

                for reviewer_id, reviewee_id in (
                    (client_id, freelancer_id),
                    (freelancer_id, client_id),
                ):
                    review_result = await session.execute(
                        select(Review).where(
                            Review.job_id == job_id,
                            Review.reviewer_id == reviewer_id,
                        )
                    )
                    if review_result.scalar_one_or_none() is None:
                        session.add(
                            Review(
                                job_id=job_id,
                                reviewer_id=reviewer_id,
                                reviewee_id=reviewee_id,
                                rating=3,
                                body="No review given",
                                is_published=False,
                            )
                        )

                reviews_result = await session.execute(
                    select(Review).where(Review.job_id == job_id)
                )
                for review in reviews_result.scalars().all():
                    review.is_published = True
                    review.published_at = now
                    session.add(review)

                await update_profile_ratings_for_user(session, client_id)
                await update_profile_ratings_for_user(session, freelancer_id)

                job_result = await session.execute(select(Job).where(Job.id == job_id))
                job = job_result.scalar_one()
                job.status = JobStatus.completed
                job.updated_at = now
                session.add(job)

                logger.info("7-day force closure completed for job_id=%s", job_id)

            await session.commit()
        except Exception:
            await session.rollback()
            raise


def start_scheduler() -> None:
    scheduler.add_job(send_review_reminders, "interval", hours=1, id="review_reminders")
    scheduler.add_job(force_close_stale_jobs, "interval", hours=1, id="force_closure")
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
