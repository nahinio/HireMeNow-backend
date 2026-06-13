from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole

RegisterRole = Literal[UserRole.freelancer, UserRole.client]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: RegisterRole
    display_name: str | None = None
    company_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    is_banned: bool
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None
    profile_picture_url: str | None = None
    company_name: str | None = None

    model_config = {"from_attributes": True}


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_token: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class PasswordResetConfirmResponse(BaseModel):
    message: str = "Password has been reset successfully"
