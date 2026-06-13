from uuid import UUID

from fastapi import FastAPI

from app.models.messaging import Conversation, Message
from app.schemas.messaging import ConversationListItem, MessageResponse


def message_payload(message: Message) -> dict:
    return MessageResponse.model_validate(message).model_dump(mode="json")


def conversation_payload(
    conversation: Conversation, *, job_title: str = ""
) -> dict:
    data = ConversationListItem(
        id=conversation.id,
        client_id=conversation.client_id,
        freelancer_id=conversation.freelancer_id,
        job_id=conversation.job_id,
        phase=conversation.phase,
        created_at=conversation.created_at,
        job_title=job_title,
    ).model_dump(mode="json")
    return data


async def notify_message_new(
    app: FastAPI,
    *,
    message: Message,
    conversation: Conversation,
) -> None:
    hub = app.state.realtime_hub
    payload = {
        "message": message_payload(message),
        "conversation_id": str(conversation.id),
    }
    await hub.send_to_users(
        [conversation.client_id, conversation.freelancer_id],
        "message.new",
        payload,
    )


async def notify_messages_read(
    app: FastAPI,
    *,
    conversation: Conversation,
    reader_id: UUID,
    message_ids: list[UUID],
) -> None:
    if not message_ids:
        return
    hub = app.state.realtime_hub
    other_id = (
        conversation.freelancer_id
        if reader_id == conversation.client_id
        else conversation.client_id
    )
    await hub.send_to_user(
        other_id,
        "messages.read",
        {
            "conversation_id": str(conversation.id),
            "reader_id": str(reader_id),
            "message_ids": [str(mid) for mid in message_ids],
        },
    )


async def notify_conversation_created(
    app: FastAPI,
    *,
    conversation: Conversation,
    message: Message,
    job_title: str,
) -> None:
    hub = app.state.realtime_hub
    await hub.send_to_users(
        [conversation.client_id, conversation.freelancer_id],
        "conversation.created",
        {
            "conversation": conversation_payload(conversation, job_title=job_title),
            "message": message_payload(message),
        },
    )


async def notify_conversation_locked(
    app: FastAPI,
    *,
    conversation: Conversation,
) -> None:
    hub = app.state.realtime_hub
    await hub.send_to_users(
        [conversation.client_id, conversation.freelancer_id],
        "conversation.locked",
        {
            "conversation_id": str(conversation.id),
            "phase": conversation.phase.value,
        },
    )
