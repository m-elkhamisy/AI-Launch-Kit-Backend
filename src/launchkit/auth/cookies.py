"""Signed cookie helpers for OAuth pending state and session tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from fastapi import Response
from starlette.requests import Request


def _sign(payload: str, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


def dump_signed(data: dict[str, Any], secret: str) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode("utf-8")).decode(
        "ascii"
    )
    return f"{raw}.{_sign(raw, secret)}"


def load_signed(token: str, secret: str) -> dict[str, Any] | None:
    try:
        raw, signature = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = _sign(raw, secret)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = base64.urlsafe_b64decode(raw + "==")
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def cookie_secure(environment: str) -> bool:
    return environment in {"staging", "production"}


def set_cookie(
    response: Response,
    *,
    name: str,
    value: str,
    max_age: int,
    environment: str,
    http_only: bool = True,
) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=http_only,
        secure=cookie_secure(environment),
        samesite="lax",
        path="/",
    )


def clear_cookie(response: Response, *, name: str, environment: str) -> None:
    response.delete_cookie(
        key=name,
        path="/",
        httponly=True,
        secure=cookie_secure(environment),
        samesite="lax",
    )


def read_cookie(request: Request, name: str) -> str | None:
    value = request.cookies.get(name)
    return value if value else None
