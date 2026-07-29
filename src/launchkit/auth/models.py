"""Auth API response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuthUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    cognito_user_id: str | None = Field(default=None, alias="cognitoUserId")
    email: str | None = None
    phone: str | None = None
    full_name: str | None = Field(default=None, alias="fullName")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    company_name: str | None = Field(default=None, alias="companyName")
    role: str | None = None
    pool: str | None = None
    email_verified: bool | None = Field(default=None, alias="emailVerified")
    phone_verified: bool | None = Field(default=None, alias="phoneVerified")
    created_at: str | None = Field(default=None, alias="createdAt")


class AuthMeResponse(BaseModel):
    authenticated: bool
    user: AuthUser | None = None


class AuthMessageResponse(BaseModel):
    message: str
