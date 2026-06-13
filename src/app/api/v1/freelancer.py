from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_freelancer
from app.db.engine import get_async_session
from app.models.user import FreelancerProfile, PortfolioLink, User
from app.schemas.freelancer import (
    FreelancerProfileResponse,
    FreelancerProfileUpdate,
    PortfolioLinkCreate,
    PortfolioLinkResponse,
    PortfolioLinkUpdate,
)
from app.schemas.profile import ProfileDeleteResponse
from app.schemas.upload import FileUploadResponse
from app.services.profile import soft_delete_freelancer
from app.services.uploads import delete_upload_if_local, save_image_upload, save_resume_upload
from app.utils.response_cache import invalidate_prefix

router = APIRouter(prefix="/freelancer", tags=["freelancer"])


def _invalidate_public_freelancer_cache() -> None:
    """Drop cached public talent listings so profile edits show immediately."""
    invalidate_prefix("freelancers:list:")


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


async def _get_profile_portfolio_links(
    session: AsyncSession, profile_id: UUID
) -> list[PortfolioLinkResponse]:
    result = await session.execute(
        select(PortfolioLink)
        .where(PortfolioLink.profile_id == profile_id)
        .order_by(PortfolioLink.position.asc(), PortfolioLink.label.asc())
    )
    return [
        PortfolioLinkResponse.model_validate(link)
        for link in result.scalars().all()
    ]


async def _profile_response(
    session: AsyncSession, profile: FreelancerProfile
) -> FreelancerProfileResponse:
    links = await _get_profile_portfolio_links(session, profile.id)
    base = FreelancerProfileResponse.model_validate(profile)
    return base.model_copy(update={"portfolio_links": links})


async def _get_owned_portfolio_link(
    session: AsyncSession,
    *,
    profile_id: UUID,
    link_id: UUID,
) -> PortfolioLink:
    result = await session.execute(
        select(PortfolioLink).where(
            PortfolioLink.id == link_id,
            PortfolioLink.profile_id == profile_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio link not found",
        )
    return link


@router.get("/profile", response_model=FreelancerProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FreelancerProfileResponse:
    profile = await _get_freelancer_profile(session, current_user.id)
    return await _profile_response(session, profile)


@router.patch("/profile", response_model=FreelancerProfileResponse)
async def update_profile(
    payload: FreelancerProfileUpdate,
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FreelancerProfileResponse:
    profile = await _get_freelancer_profile(session, current_user.id)

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.profile_picture_url is not None:
        profile.profile_picture_url = payload.profile_picture_url
    if payload.resume_url is not None:
        profile.resume_url = payload.resume_url
    if payload.linkedin_url is not None:
        profile.linkedin_url = payload.linkedin_url
    if payload.contact_email is not None:
        profile.contact_email = payload.contact_email
    if payload.github_url is not None:
        profile.github_url = payload.github_url
    if payload.portfolio_url is not None:
        profile.portfolio_url = payload.portfolio_url
    if payload.available_for_work is not None:
        profile.available_for_work = payload.available_for_work

    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    _invalidate_public_freelancer_cache()
    return await _profile_response(session, profile)


@router.post("/profile/picture", response_model=FileUploadResponse)
async def upload_profile_picture(
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    file: Annotated[UploadFile, File(...)],
) -> FileUploadResponse:
    settings = get_settings()
    profile = await _get_freelancer_profile(session, current_user.id)

    url = await save_image_upload(
        file,
        owner_id=current_user.id,
        category="freelancers/profile-picture",
        max_bytes=settings.MAX_IMAGE_SIZE_BYTES,
    )
    delete_upload_if_local(profile.profile_picture_url)
    profile.profile_picture_url = url
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    _invalidate_public_freelancer_cache()
    return FileUploadResponse(url=url)


@router.post("/profile/resume", response_model=FileUploadResponse)
async def upload_resume(
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    file: Annotated[UploadFile, File(...)],
) -> FileUploadResponse:
    profile = await _get_freelancer_profile(session, current_user.id)

    url = await save_resume_upload(file, owner_id=current_user.id)
    delete_upload_if_local(profile.resume_url)
    profile.resume_url = url
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    _invalidate_public_freelancer_cache()
    return FileUploadResponse(url=url)


@router.delete("/profile", response_model=ProfileDeleteResponse)
async def delete_profile(
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ProfileDeleteResponse:
    deleted_at = await soft_delete_freelancer(session, current_user)
    return ProfileDeleteResponse(user_id=current_user.id, deleted_at=deleted_at)


@router.get("/portfolio", response_model=list[PortfolioLinkResponse])
async def list_portfolio_links(
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[PortfolioLinkResponse]:
    profile = await _get_freelancer_profile(session, current_user.id)
    return await _get_profile_portfolio_links(session, profile.id)


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
        label=payload.label.strip(),
        url=payload.url.strip(),
        position=payload.position,
    )
    session.add(link)
    _invalidate_public_freelancer_cache()
    return link


@router.patch("/portfolio/{link_id}", response_model=PortfolioLinkResponse)
async def update_portfolio_link(
    link_id: UUID,
    payload: PortfolioLinkUpdate,
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PortfolioLink:
    profile = await _get_freelancer_profile(session, current_user.id)
    link = await _get_owned_portfolio_link(
        session, profile_id=profile.id, link_id=link_id
    )

    if payload.label is not None:
        link.label = payload.label.strip()
    if payload.url is not None:
        link.url = payload.url.strip()
    if payload.position is not None:
        link.position = payload.position

    session.add(link)
    _invalidate_public_freelancer_cache()
    return link


@router.delete("/portfolio/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_link(
    link_id: UUID,
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    profile = await _get_freelancer_profile(session, current_user.id)
    link = await _get_owned_portfolio_link(
        session, profile_id=profile.id, link_id=link_id
    )
    await session.delete(link)
    _invalidate_public_freelancer_cache()
