from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_client
from app.db.engine import get_async_session
from app.models.user import ClientProfile, User
from app.schemas.client import ClientProfileResponse, ClientProfileUpdate
from app.schemas.profile import ProfileDeleteResponse
from app.schemas.upload import FileUploadResponse
from app.services.profile import soft_delete_client
from app.services.uploads import delete_upload_if_local, save_image_upload

router = APIRouter(prefix="/client", tags=["client"])


async def _get_client_profile(session: AsyncSession, user_id) -> ClientProfile:
    result = await session.execute(
        select(ClientProfile).where(ClientProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client profile not found",
        )
    return profile


@router.get("/profile", response_model=ClientProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ClientProfile:
    return await _get_client_profile(session, current_user.id)


@router.patch("/profile", response_model=ClientProfileResponse)
async def update_profile(
    payload: ClientProfileUpdate,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ClientProfile:
    profile = await _get_client_profile(session, current_user.id)

    if payload.company_name is not None:
        profile.company_name = payload.company_name
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.profile_picture_url is not None:
        profile.profile_picture_url = payload.profile_picture_url
    if payload.company_link is not None:
        profile.company_link = payload.company_link

    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    await session.refresh(profile)
    return profile


@router.post("/profile/picture", response_model=FileUploadResponse)
async def upload_profile_picture(
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    file: Annotated[UploadFile, File(...)],
) -> FileUploadResponse:
    settings = get_settings()
    profile = await _get_client_profile(session, current_user.id)

    url = await save_image_upload(
        file,
        owner_id=current_user.id,
        category="clients/profile-picture",
        max_bytes=settings.MAX_IMAGE_SIZE_BYTES,
    )
    delete_upload_if_local(profile.profile_picture_url)
    profile.profile_picture_url = url
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)
    await session.refresh(profile)
    return FileUploadResponse(url=url)


@router.delete("/profile", response_model=ProfileDeleteResponse)
async def delete_profile(
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ProfileDeleteResponse:
    deleted_at = await soft_delete_client(session, current_user)
    return ProfileDeleteResponse(user_id=current_user.id, deleted_at=deleted_at)
