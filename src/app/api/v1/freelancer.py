from datetime import datetime, timezone
from typing import Annotated

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
)
from app.schemas.profile import ProfileDeleteResponse
from app.schemas.upload import FileUploadResponse
from app.services.profile import soft_delete_freelancer
from app.services.uploads import delete_upload_if_local, save_image_upload, save_resume_upload

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


@router.get("/profile", response_model=FreelancerProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FreelancerProfile:
    return await _get_freelancer_profile(session, current_user.id)


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
    await session.refresh(profile)
    return profile


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
    await session.refresh(profile)
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
    await session.refresh(profile)
    return FileUploadResponse(url=url)


@router.delete("/profile", response_model=ProfileDeleteResponse)
async def delete_profile(
    current_user: Annotated[User, Depends(require_freelancer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ProfileDeleteResponse:
    deleted_at = await soft_delete_freelancer(session, current_user)
    return ProfileDeleteResponse(user_id=current_user.id, deleted_at=deleted_at)


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
