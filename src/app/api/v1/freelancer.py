from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_freelancer
from app.db.engine import get_async_session
from app.models.user import FreelancerProfile, PortfolioLink, User
from app.schemas.freelancer import (
    FreelancerProfileResponse,
    FreelancerProfileUpdate,
    PortfolioLinkCreate,
    PortfolioLinkResponse,
)

router = APIRouter(prefix="/freelancer", tags=["freelancer"])


async def _get_freelancer_profile(
    session: AsyncSession, user_id
) -> FreelancerProfile:
    result = await session.execute(
        select(FreelancerProfile).where(FreelancerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer profile not found",
        )
    return profile


@router.patch("/profile", response_model=FreelancerProfileResponse)
async def update_profile(
    payload: FreelancerProfileUpdate,
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FreelancerProfile:
    profile = await _get_freelancer_profile(session, current_user.id)

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.available_for_work is not None:
        profile.available_for_work = payload.available_for_work

    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    await session.refresh(profile)
    return profile


@router.post(
    "/portfolio",
    response_model=PortfolioLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_portfolio_link(
    payload: PortfolioLinkCreate,
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PortfolioLink:
    profile = await _get_freelancer_profile(session, current_user.id)
    link = PortfolioLink(
        profile_id=profile.id,
        label=payload.label,
        url=payload.url,
        position=payload.position,
    )
    session.add(link)
    await session.flush()
    await session.refresh(link)
    return link
