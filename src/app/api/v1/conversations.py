from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_client
from app.db.engine import get_async_session
from app.models.enums import ApplicationStatus, ConversationPhase
from app.models.job import Application, Job
from app.models.messaging import CompletionSignal, Conversation, Message
from app.models.user import FreelancerProfile, User
from app.schemas.messaging import (
    ConversationInitiateRequest,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _get_conversation(
    session: AsyncSession, conversation_id: UUID
) -> Conversation:
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


def _verify_conversation_party(conversation: Conversation, user: User) -> None:
    if user.id not in (conversation.client_id, conversation.freelancer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a party to this conversation",
        )


async def _check_conversation_locked(
    session: AsyncSession, conversation: Conversation
) -> None:
    if conversation.phase == ConversationPhase.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conversation is locked.",
        )

    signal_result = await session.execute(
        select(CompletionSignal.id)
        .where(CompletionSignal.job_id == conversation.job_id)
        .limit(1)
    )
    if signal_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conversation is locked.",
        )


@router.post("/initiate", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def initiate_conversation(
    payload: ConversationInitiateRequest,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Conversation:
    job_result = await session.execute(select(Job).where(Job.id == payload.job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the job owner can initiate conversations",
        )

    application_result = await session.execute(
        select(Application)
        .join(FreelancerProfile, Application.freelancer_id == FreelancerProfile.id)
        .where(
            Application.job_id == payload.job_id,
            FreelancerProfile.user_id == payload.freelancer_id,
            Application.status == ApplicationStatus.accepted,
        )
    )
    if application_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select an applicant before starting a conversation",
        )

    existing_result = await session.execute(
        select(Conversation).where(
            Conversation.job_id == payload.job_id,
            Conversation.freelancer_id == payload.freelancer_id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation already exists",
        )

    conversation = Conversation(
        client_id=current_user.id,
        freelancer_id=payload.freelancer_id,
        job_id=payload.job_id,
    )
    session.add(conversation)
    await session.flush()
    await session.refresh(conversation)
    return conversation


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Message:
    conversation = await _get_conversation(session, conversation_id)
    _verify_conversation_party(conversation, current_user)
    await _check_conversation_locked(session, conversation)

    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=payload.body,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return message


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[Message]:
    conversation = await _get_conversation(session, conversation_id)
    _verify_conversation_party(conversation, current_user)

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.asc())
    )
    messages = result.scalars().all()

    await session.execute(
        update(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.sender_id != current_user.id,
            Message.is_read.is_(False),
        )
        .values(is_read=True)
    )

    return messages
