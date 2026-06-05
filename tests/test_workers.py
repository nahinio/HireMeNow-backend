import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.enums import ApplicationStatus, JobStatus, UserRole
from app.models.job import Application, Job
from app.models.messaging import CompletionSignal
from app.models.review import Review
from app.models.user import ClientProfile, FreelancerProfile, User
from app.workers.scheduler import force_close_stale_jobs

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Worker tests require TEST_DATABASE_URL",
)


@pytest.mark.asyncio
async def test_worker_b_force_closure(db_session):
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=8)

    client = User(
        email=f"client-{uuid4()}@test.com",
        password_hash="hash",
        role=UserRole.client,
    )
    freelancer_user = User(
        email=f"freelancer-{uuid4()}@test.com",
        password_hash="hash",
        role=UserRole.freelancer,
    )
    db_session.add(client)
    db_session.add(freelancer_user)
    await db_session.flush()

    client_profile = ClientProfile(user_id=client.id, company_name="Co")
    freelancer_profile = FreelancerProfile(
        user_id=freelancer_user.id,
        display_name="Dev",
    )
    db_session.add(client_profile)
    db_session.add(freelancer_profile)
    await db_session.flush()

    job = Job(
        client_id=client.id,
        title="Job",
        description="Desc",
        deliverables="Del",
        budget=Decimal("100"),
        timeline="1w",
        status=JobStatus.pending_confirmation,
    )
    db_session.add(job)
    await db_session.flush()

    db_session.add(
        Application(
            freelancer_id=freelancer_profile.id,
            job_id=job.id,
            quiz_score_snapshot=Decimal("90"),
            status=ApplicationStatus.accepted,
        )
    )
    db_session.add(
        CompletionSignal(job_id=job.id, signalled_by=client.id, signalled_at=old)
    )
    db_session.add(
        CompletionSignal(
            job_id=job.id, signalled_by=freelancer_user.id, signalled_at=old
        )
    )
    db_session.add(
        Review(
            job_id=job.id,
            reviewer_id=client.id,
            reviewee_id=freelancer_user.id,
            rating=5,
            body="Great work overall, very professional.",
            is_published=False,
        )
    )
    await db_session.commit()

    await force_close_stale_jobs()

    result = await db_session.execute(select(Review).where(Review.job_id == job.id))
    reviews = result.scalars().all()
    assert len(reviews) == 2
    assert all(review.is_published for review in reviews)
    assert any(review.body == "No review given" for review in reviews)

    job_result = await db_session.execute(select(Job).where(Job.id == job.id))
    updated_job = job_result.scalar_one()
    assert updated_job.status == JobStatus.completed
