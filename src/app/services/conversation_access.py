from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ConversationPhase
from app.models.messaging import CompletionSignal, Conversation
from app.models.user import User


async def get_conversation_or_404(
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


def verify_conversation_party(conversation: Conversation, user: User) -> None:
    if user.id not in (conversation.client_id, conversation.freelancer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a party to this conversation",
        )


async def ensure_conversation_active(
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
