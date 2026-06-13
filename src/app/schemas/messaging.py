from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import ConversationPhase


class ConversationInitiateRequest(BaseModel):
    job_id: UUID
    freelancer_id: UUID


class ConversationResponse(BaseModel):
    id: UUID
    client_id: UUID
    freelancer_id: UUID
    job_id: UUID
    phase: ConversationPhase
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationListItem(ConversationResponse):
    job_title: str


class MessageCreate(BaseModel):
    body: str


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID | None
    body: str
    is_system: bool
    is_read: bool
    sent_at: datetime

    model_config = {"from_attributes": True}
