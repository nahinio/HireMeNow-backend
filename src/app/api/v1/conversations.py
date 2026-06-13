from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_client
from app.db.engine import get_async_session
from app.models.job import Job
from app.models.messaging import Conversation, Message
from app.models.user import User
from app.schemas.messaging import (
    ConversationInitiateRequest,
    ConversationListItem,
    MessageCreate,
    MessageResponse,
)
from app.services.chat_events import notify_message_new, notify_messages_read
from app.services.conversation_access import (
    ensure_conversation_active,
    get_conversation_or_404,
    verify_conversation_party,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationListItem])
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ConversationListItem]:
    result = await session.execute(
        select(Conversation, Job.title)
        .join(Job, Conversation.job_id == Job.id)
        .where(
            or_(
                Conversation.client_id == current_user.id,
                Conversation.freelancer_id == current_user.id,
            )
        )
        .order_by(Conversation.created_at.desc())
    )
    return [
        ConversationListItem(
            id=conversation.id,
            client_id=conversation.client_id,
            freelancer_id=conversation.freelancer_id,
            job_id=conversation.job_id,
            phase=conversation.phase,
            created_at=conversation.created_at,
            job_title=job_title,
        )
        for conversation, job_title in result.all()
    ]


@router.get("/{conversation_id}", response_model=ConversationListItem)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ConversationListItem:
    result = await session.execute(
        select(Conversation, Job.title)
        .join(Job, Conversation.job_id == Job.id)
        .where(Conversation.id == conversation_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    conversation, job_title = row
    verify_conversation_party(conversation, current_user)
    return ConversationListItem(
        id=conversation.id,
        client_id=conversation.client_id,
        freelancer_id=conversation.freelancer_id,
        job_id=conversation.job_id,
        phase=conversation.phase,
        created_at=conversation.created_at,
        job_title=job_title,
    )


@router.post("/initiate", status_code=status.HTTP_403_FORBIDDEN)
async def initiate_conversation(
    payload: ConversationInitiateRequest,
    current_user: Annotated[User, Depends(require_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Conversations are created automatically when you hire a freelancer",
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Message:
    conversation = await get_conversation_or_404(session, conversation_id)
    verify_conversation_party(conversation, current_user)
    await ensure_conversation_active(session, conversation)

    body = payload.body.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message body cannot be empty",
        )

    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=body,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    await notify_message_new(
        request.app,
        message=message,
        conversation=conversation,
    )
    return message


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[Message]:
    conversation = await get_conversation_or_404(session, conversation_id)
    verify_conversation_party(conversation, current_user)

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.asc())
    )
    messages = result.scalars().all()

    unread_ids = [
        message.id
        for message in messages
        if not message.is_read
        and message.sender_id is not None
        and message.sender_id != current_user.id
    ]
    if unread_ids:
        await session.execute(
            update(Message)
            .where(Message.id.in_(unread_ids))
            .values(is_read=True)
        )
        await notify_messages_read(
            request.app,
            conversation=conversation,
            reader_id=current_user.id,
            message_ids=unread_ids,
        )

    return messages
