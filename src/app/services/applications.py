from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ApplicationStatus, JobStatus
from app.models.job import Application, Job
from app.models.messaging import Conversation, Message
from app.models.user import FreelancerProfile, User

SELECTION_MESSAGE = (
    'Congratulations! You have been selected for the job "{title}". '
    "You can reply here to coordinate next steps."
)


async def select_applicant_for_job(
    session: AsyncSession,
    *,
    job: Job,
    client: User,
    application_id: UUID,
) -> tuple[Application, Conversation, Message]:
    if job.client_id != client.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to select applicants for this job",
        )
    if job.status != JobStatus.open:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Applicants can only be selected for open jobs",
        )

    result = await session.execute(
        select(Application, FreelancerProfile, User)
        .join(FreelancerProfile, Application.freelancer_id == FreelancerProfile.id)
        .join(User, FreelancerProfile.user_id == User.id)
        .where(
            Application.id == application_id,
            Application.job_id == job.id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found for this job",
        )

    application, profile, freelancer_user = row

    if application.status != ApplicationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only pending applications can be selected",
        )
    if freelancer_user.is_banned or freelancer_user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Freelancer is not eligible for selection",
        )
    if not profile.available_for_work:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot select a freelancer who is not available for work",
        )

    existing_accepted = await session.execute(
        select(Application.id).where(
            Application.job_id == job.id,
            Application.status == ApplicationStatus.accepted,
        )
    )
    if existing_accepted.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A freelancer has already been selected for this job",
        )

    application.status = ApplicationStatus.accepted
    session.add(application)

    await session.execute(
        update(Application)
        .where(
            Application.job_id == job.id,
            Application.id != application.id,
            Application.status == ApplicationStatus.pending,
        )
        .values(status=ApplicationStatus.rejected)
    )

    conversation_result = await session.execute(
        select(Conversation).where(
            Conversation.job_id == job.id,
            Conversation.freelancer_id == freelancer_user.id,
        )
    )
    conversation = conversation_result.scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(
            client_id=client.id,
            freelancer_id=freelancer_user.id,
            job_id=job.id,
        )
        session.add(conversation)
        await session.flush()

    message = Message(
        conversation_id=conversation.id,
        sender_id=client.id,
        body=SELECTION_MESSAGE.format(title=job.title),
    )
    session.add(message)

    job.status = JobStatus.filled
    job.updated_at = datetime.now(timezone.utc)
    session.add(job)

    await session.flush()
    await session.refresh(application)
    await session.refresh(conversation)
    await session.refresh(message)
    return application, conversation, message
