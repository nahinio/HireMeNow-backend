from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.enums import ApplicationStatus, JobStatus, ReportStatus
from app.models.job import Application, Job
from app.models.report import UserReport
from app.models.skill import Skill
from app.models.user import FreelancerProfile
from app.schemas.admin import AdminStatsResponse


async def get_admin_stats(session: AsyncSession) -> AdminStatsResponse:
    pending_reports = int(
        (
            await session.execute(
                select(func.count())
                .select_from(UserReport)
                .where(UserReport.status == ReportStatus.pending)
            )
        ).scalar_one()
    )

    job_counts = (
        await session.execute(
            select(
                func.count().label("total"),
                func.count().filter(Job.status == JobStatus.open).label("open"),
                func.count().filter(Job.status == JobStatus.filled).label("filled"),
                func.count()
                .filter(Job.status == JobStatus.pending_confirmation)
                .label("pending_confirmation"),
                func.count().filter(Job.status == JobStatus.completed).label("completed"),
                func.count().filter(Job.status == JobStatus.closed).label("closed"),
            ).select_from(Job)
        )
    ).one()

    app_counts = (
        await session.execute(
            select(
                func.count().label("total"),
                func.count()
                .filter(Application.status == ApplicationStatus.pending)
                .label("pending"),
            ).select_from(Application)
        )
    ).one()

    total_courses = int(
        (await session.execute(select(func.count()).select_from(Course))).scalar_one()
    )
    total_freelancers = int(
        (
            await session.execute(select(func.count()).select_from(FreelancerProfile))
        ).scalar_one()
    )
    total_skills = int(
        (await session.execute(select(func.count()).select_from(Skill))).scalar_one()
    )

    return AdminStatsResponse(
        pending_reports=pending_reports,
        total_jobs=int(job_counts.total or 0),
        open_jobs=int(job_counts.open or 0),
        filled_jobs=int(job_counts.filled or 0),
        pending_confirmation_jobs=int(job_counts.pending_confirmation or 0),
        completed_jobs=int(job_counts.completed or 0),
        closed_jobs=int(job_counts.closed or 0),
        total_courses=total_courses,
        total_freelancers=total_freelancers,
        total_skills=total_skills,
        total_applications=int(app_counts.total or 0),
        pending_applications=int(app_counts.pending or 0),
    )
