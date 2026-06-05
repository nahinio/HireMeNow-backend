from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProfileDeleteResponse(BaseModel):
    user_id: UUID
    deleted_at: datetime
