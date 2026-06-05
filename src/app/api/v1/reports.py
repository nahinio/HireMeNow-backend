from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.engine import get_async_session
from app.models.user import User
from app.schemas.report import UserReportCreate, UserReportResponse
from app.services.reports import create_user_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=UserReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(
    payload: UserReportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserReportResponse:
    report = await create_user_report(
        session,
        reporter=current_user,
        reported_user_id=payload.reported_user_id,
        description=payload.description,
    )
    return UserReportResponse.model_validate(report)
