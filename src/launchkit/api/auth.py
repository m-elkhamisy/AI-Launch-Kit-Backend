"""Temporary fixed-account authentication for restricted staging releases."""

from datetime import UTC, datetime, timedelta
from secrets import compare_digest
from typing import Any

import jwt
from jwt import InvalidTokenError
from pydantic import Field, SecretStr

from launchkit.core.config import Settings
from launchkit.core.exceptions import AuthenticationError, ConfigurationError
from launchkit.core.models import AliasedModel

LOCAL_OTP = "123456"
LOCAL_TOKEN_SECRET = "launchkit-local-development-token-secret"
TOKEN_ALGORITHM = "HS256"
TOKEN_AUDIENCE = "ai-launch-kit-api"
TOKEN_ISSUER = "ai-launch-kit"


class AccessCodeRequest(AliasedModel):
    email: str = Field(min_length=3, max_length=254)


class AccessCodeResponse(AliasedModel):
    status: str = "accepted"


class VerifyAccessCodeRequest(AccessCodeRequest):
    code: str = Field(pattern=r"^\d{6}$")


class AuthTokenResponse(AliasedModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


def request_access_code(settings: Settings, email: str) -> AccessCodeResponse:
    _verify_email(settings, email)
    return AccessCodeResponse()


def verify_access_code(settings: Settings, email: str, code: str) -> AuthTokenResponse:
    normalized_email = _verify_email(settings, email)
    expected_code = _secret_value(settings, settings.auth_otp, LOCAL_OTP, "staging OTP")
    if not compare_digest(code, expected_code):
        raise AuthenticationError("The email or access code is invalid.")

    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.auth_token_ttl_seconds)
    payload = {
        "sub": normalized_email,
        "aud": TOKEN_AUDIENCE,
        "iss": TOKEN_ISSUER,
        "iat": now,
        "exp": expires_at,
    }
    secret = _secret_value(
        settings,
        settings.auth_token_secret,
        LOCAL_TOKEN_SECRET,
        "authentication token secret",
    )
    token = jwt.encode(payload, secret, algorithm=TOKEN_ALGORITHM)
    return AuthTokenResponse(
        access_token=token,
        expires_in_seconds=settings.auth_token_ttl_seconds,
    )


def authenticate_token(settings: Settings, token: str) -> str:
    secret = _secret_value(
        settings,
        settings.auth_token_secret,
        LOCAL_TOKEN_SECRET,
        "authentication token secret",
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=[TOKEN_ALGORITHM],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
        )
    except InvalidTokenError as exc:
        raise AuthenticationError("The access session is invalid or expired.") from exc
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthenticationError("The access session is invalid or expired.")
    return subject


def _verify_email(settings: Settings, email: str) -> str:
    normalized = email.strip().lower()
    if not compare_digest(normalized, settings.auth_email.strip().lower()):
        raise AuthenticationError("The email or access code is invalid.")
    return normalized


def _secret_value(
    settings: Settings,
    configured: SecretStr | None,
    local_default: str,
    label: str,
) -> str:
    if configured is not None:
        value = configured.get_secret_value()
        if value:
            return value
    if settings.environment in {"local", "test"}:
        return local_default
    raise ConfigurationError(f"The {label} is not configured")
