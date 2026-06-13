import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from starlette.websockets import WebSocketState

from app.core.security import decode_token_subject
from app.db.engine import async_session_maker
from app.models.messaging import Conversation, Message
from app.models.user import TokenBlocklist, User
from app.services.chat_events import notify_message_new
from app.services.conversation_access import ensure_conversation_active
from app.services.realtime import RealtimeHub

router = APIRouter(tags=["realtime"])


async def _authenticate_ws_user(token: str) -> User | None:
    user_id = decode_token_subject(token)
    if user_id is None:
        return None

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.is_banned or user.is_deleted:
            return None

        blocklist_result = await session.execute(
            select(TokenBlocklist).where(TokenBlocklist.user_id == user.id)
        )
        if blocklist_result.scalar_one_or_none() is not None:
            return None
        return user


async def _persist_ws_message(
    *,
    user_id: UUID,
    conversation_id: UUID,
    body: str,
) -> tuple[Message, Conversation] | None:
    trimmed = body.strip()
    if not trimmed:
        return None

    async with async_session_maker() as session:
        conv_result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        if conversation is None:
            return None
        if user_id not in (conversation.client_id, conversation.freelancer_id):
            return None

        try:
            await ensure_conversation_active(session, conversation)
        except HTTPException:
            return None

        message = Message(
            conversation_id=conversation_id,
            sender_id=user_id,
            body=trimmed,
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message, conversation


@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: Annotated[str, Query()],
) -> None:
    user = await _authenticate_ws_user(token)
    if user is None:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    hub: RealtimeHub = websocket.app.state.realtime_hub
    await hub.connect(user.id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                continue

            frame_type = frame.get("type")
            if frame_type == "ping":
                await websocket.send_text(
                    json.dumps({"event": "pong", "data": {}})
                )
                continue

            if frame_type == "send_message":
                conversation_id_raw = frame.get("conversation_id")
                body = frame.get("body", "")
                if not conversation_id_raw:
                    continue
                try:
                    conversation_id = UUID(str(conversation_id_raw))
                except (TypeError, ValueError):
                    continue

                saved = await _persist_ws_message(
                    user_id=user.id,
                    conversation_id=conversation_id,
                    body=str(body),
                )
                if saved is None:
                    continue
                message, conversation = saved
                await notify_message_new(
                    websocket.app,
                    message=message,
                    conversation=conversation,
                )
    except WebSocketDisconnect:
        pass
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await hub.disconnect(websocket)
