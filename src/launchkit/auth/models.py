"""Auth API response models."""

from __future__ import annotations

from typing import Any

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
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    authenticated: bool
    user: AuthUser | None = None
    # Debug helpers: owner_id is Cognito UUID; licenseNumber is best-effort IC login id.
    owner_id: str | None = Field(default=None, alias="ownerId")
    license_number: str | None = Field(default=None, alias="licenseNumber")
    profile: dict[str, Any] | None = None


class AuthMessageResponse(BaseModel):
    message: str
