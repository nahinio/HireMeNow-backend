from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.review import Review
from app.models.user import ClientProfile, FreelancerProfile, User


async def recalculate_profile_ratings(
    session: AsyncSession, reviewee_id: UUID
) -> tuple[Decimal, int]:
    result = await session.execute(
        select(func.avg(Review.rating), func.count())
        .where(
            Review.reviewee_id == reviewee_id,
            Review.is_published.is_(True),
            Review.is_deleted.is_(False),
        )
    )
    avg_rating, review_count = result.one()
    avg_value = Decimal(str(avg_rating)) if avg_rating is not None else Decimal("0")
    count_value = int(review_count or 0)
    return avg_value, count_value


async def update_profile_ratings_for_user(
    session: AsyncSession, user_id: UUID
) -> None:
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one()
    avg_rating, review_count = await recalculate_profile_ratings(session, user_id)

    if user.role == UserRole.freelancer:
        profile_result = await session.execute(
            select(FreelancerProfile).where(FreelancerProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one()
        profile.avg_rating = avg_rating
        profile.review_count = review_count
        session.add(profile)
    elif user.role == UserRole.client:
        profile_result = await session.execute(
            select(ClientProfile).where(ClientProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one()
        profile.avg_rating = avg_rating
        profile.review_count = review_count
        session.add(profile)
