"""PKCE helpers for OAuth 2.0 Authorization Code flow."""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_code_verifier(length: int = 64) -> str:
    """Return a high-entropy URL-safe verifier (43–128 characters)."""

    verifier = secrets.token_urlsafe(48)
    if length < 43:
        length = 43
    if length > 128:
        length = 128
    return verifier[:length]


def code_challenge_s256(verifier: str) -> str:
    """BASE64URL(SHA256(verifier)) without padding."""

    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_state() -> str:
    """Return a CSRF state token."""

    return secrets.token_urlsafe(32)
