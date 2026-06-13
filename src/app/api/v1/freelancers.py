from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import async_session_maker, get_async_session
from app.models.skill import Skill, SkillBadge
from app.models.user import FreelancerProfile, PortfolioLink, User
from app.schemas.freelancer import PortfolioLinkResponse
from app.schemas.report import FreelancerPublicListResponse, FreelancerPublicResponse
from app.schemas.skill import SkillResponse
from app.utils.availability import serialize_availability
from app.utils.response_cache import get_cached, set_cached

router = APIRouter(prefix="/freelancers", tags=["freelancers"])


async def _get_profile_skills(
    session: AsyncSession, profile_id: UUID
) -> list[SkillResponse]:
    result = await session.execute(
        select(Skill)
        .join(SkillBadge, SkillBadge.skill_id == Skill.id)
        .where(SkillBadge.profile_id == profile_id, Skill.is_active.is_(True))
    )
    return [SkillResponse.model_validate(skill) for skill in result.scalars().all()]


async def _bulk_get_profile_skills(
    session: AsyncSession, profile_ids: list[UUID]
) -> dict[UUID, list[SkillResponse]]:
    if not profile_ids:
        return {}
    result = await session.execute(
        select(SkillBadge.profile_id, Skill)
        .join(Skill, SkillBadge.skill_id == Skill.id)
        .where(
            SkillBadge.profile_id.in_(profile_ids),
            Skill.is_active.is_(True),
        )
        .order_by(Skill.name.asc())
    )
    skills_by_profile: dict[UUID, list[SkillResponse]] = {
        profile_id: [] for profile_id in profile_ids
    }
    for profile_id, skill in result.all():
        skills_by_profile[profile_id].append(SkillResponse.model_validate(skill))
    return skills_by_profile


def _build_public_response(
    profile: FreelancerProfile,
    skills: list[SkillResponse],
    *,
    portfolio_links: list[PortfolioLinkResponse] | None = None,
    account_email: str | None = None,
) -> FreelancerPublicResponse:
    return FreelancerPublicResponse(
        profile_id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        bio=profile.bio,
        profile_picture_url=profile.profile_picture_url,
        contact_email=profile.contact_email or account_email,
        resume_url=profile.resume_url,
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        portfolio_url=profile.portfolio_url,
        avg_rating=profile.avg_rating,
        review_count=profile.review_count,
        availability_status=serialize_availability(profile.available_for_work),
        updated_at=profile.updated_at,
        skills=skills,
        portfolio_links=portfolio_links or [],
    )


@router.get("", response_model=FreelancerPublicListResponse)
async def list_freelancers(
    q: str | None = Query(default=None, description="Search by display name"),
    available_for_work: bool | None = Query(default=None),
    skill_id: UUID | None = Query(default=None),
    min_rating: Decimal | None = Query(default=None, ge=0, le=5),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> FreelancerPublicListResponse:
    cache_key = (
        f"freelancers:list:{q}:{available_for_work}:{skill_id}:"
        f"{min_rating}:{page}:{limit}"
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    async with async_session_maker() as session:
        query = (
            select(FreelancerProfile, User.email)
            .join(User, FreelancerProfile.user_id == User.id)
            .where(
                User.is_deleted.is_(False),
                User.is_banned.is_(False),
            )
        )
        count_query = (
            select(func.count())
            .select_from(FreelancerProfile)
            .join(User, FreelancerProfile.user_id == User.id)
            .where(
                User.is_deleted.is_(False),
                User.is_banned.is_(False),
            )
        )

        if q:
            pattern = f"%{q.strip()}%"
            query = query.where(FreelancerProfile.display_name.ilike(pattern))
            count_query = count_query.where(FreelancerProfile.display_name.ilike(pattern))
        if available_for_work is not None:
            query = query.where(FreelancerProfile.available_for_work == available_for_work)
            count_query = count_query.where(
                FreelancerProfile.available_for_work == available_for_work
            )
        if min_rating is not None:
            query = query.where(FreelancerProfile.avg_rating >= min_rating)
            count_query = count_query.where(FreelancerProfile.avg_rating >= min_rating)
        if skill_id is not None:
            query = query.join(
                SkillBadge,
                SkillBadge.profile_id == FreelancerProfile.id,
            ).where(SkillBadge.skill_id == skill_id)
            count_query = count_query.join(
                SkillBadge,
                SkillBadge.profile_id == FreelancerProfile.id,
            ).where(SkillBadge.skill_id == skill_id)

        total = int((await session.execute(count_query)).scalar_one())
        result = await session.execute(
            query.order_by(FreelancerProfile.avg_rating.desc(), FreelancerProfile.display_name.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        rows = result.unique().all()
        skills_by_profile = await _bulk_get_profile_skills(
            session, [profile.id for profile, _email in rows]
        )

        items: list[FreelancerPublicResponse] = []
        for profile, account_email in rows:
            skills = skills_by_profile.get(profile.id, [])
            items.append(
                _build_public_response(
                    profile,
                    skills,
                    account_email=account_email,
                )
            )

        return set_cached(
            cache_key,
            FreelancerPublicListResponse(
                items=items,
                page=page,
                limit=limit,
                total=total,
            ),
        )


@router.get("/{profile_id}", response_model=FreelancerPublicResponse)
async def get_freelancer(
    profile_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FreelancerPublicResponse:
    result = await session.execute(
        select(FreelancerProfile, User)
        .join(User, FreelancerProfile.user_id == User.id)
        .where(
            FreelancerProfile.id == profile_id,
            User.is_deleted.is_(False),
            User.is_banned.is_(False),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Freelancer not found")

    profile, user = row
    skills = await _get_profile_skills(session, profile.id)
    links_result = await session.execute(
        select(PortfolioLink)
        .where(PortfolioLink.profile_id == profile.id)
        .order_by(PortfolioLink.position.asc())
    )
    portfolio_links = [
        PortfolioLinkResponse.model_validate(link)
        for link in links_result.scalars().all()
    ]
    return _build_public_response(
        profile,
        skills,
        portfolio_links=portfolio_links,
        account_email=user.email,
    )
