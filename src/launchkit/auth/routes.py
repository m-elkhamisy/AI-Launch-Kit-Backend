"""OAuth PKCE routes: IC-hosted login, server-side code exchange, session cookies."""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urlencode

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from launchkit.api.auth import (
    API_TOKEN_COOKIE,
    AuthTokenResponse,
    authenticate_token,
    mint_token,
    read_token_license,
)
from launchkit.auth.client import AuthServiceClient
from launchkit.auth.cookies import (
    clear_cookie,
    dump_signed,
    load_signed,
    read_cookie,
    set_cookie,
)
from launchkit.auth.models import AuthMeResponse, AuthMessageResponse, AuthUser
from launchkit.auth.pkce import code_challenge_s256, generate_code_verifier
from launchkit.builds.quota import extract_license_number
from launchkit.core.config import Settings, get_settings
from launchkit.core.exceptions import ConfigurationError, ProviderError
from launchkit.persistence import PersistenceRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_PENDING_COOKIE = "lk_oauth_pending"
ACCESS_COOKIE = "lk_access_token"
REFRESH_COOKIE = "lk_refresh_token"

ACCESS_MAX_AGE = 60 * 60
REFRESH_MAX_AGE = 60 * 60 * 24 * 30
OAUTH_PENDING_MAX_AGE = 60 * 10


def get_auth_client(settings: Annotated[Settings, Depends(get_settings)]) -> AuthServiceClient:
    return AuthServiceClient(settings)


def _frontend_redirect(settings: Settings, *, params: dict[str, str]) -> RedirectResponse:
    base = settings.auth_frontend_url.rstrip("/")
    return RedirectResponse(url=f"{base}/?{urlencode(params)}", status_code=status.HTTP_302_FOUND)


def _pending_code_verifier(request: Request, settings: Settings, state: str | None) -> str | None:
    """Resolve PKCE verifier from signed OAuth state (preferred) or pending cookie."""

    if state:
        from_state = load_signed(state, settings.auth_session_secret)
        if from_state:
            verifier = from_state.get("code_verifier")
            if isinstance(verifier, str) and verifier:
                return verifier

    pending_raw = read_cookie(request, OAUTH_PENDING_COOKIE)
    pending = load_signed(pending_raw, settings.auth_session_secret) if pending_raw else None
    if not pending:
        return None
    # Legacy cookie format: {state, code_verifier} with random OAuth state.
    expected_state = pending.get("state")
    if isinstance(expected_state, str) and state and state != expected_state:
        return None
    verifier = pending.get("code_verifier")
    return verifier if isinstance(verifier, str) and verifier else None


def _set_token_cookies(
    response: Response,
    *,
    settings: Settings,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None = None,
) -> None:
    set_cookie(
        response,
        name=ACCESS_COOKIE,
        value=access_token,
        max_age=expires_in or ACCESS_MAX_AGE,
        environment=settings.environment,
    )
    if refresh_token:
        set_cookie(
            response,
            name=REFRESH_COOKIE,
            value=refresh_token,
            max_age=REFRESH_MAX_AGE,
            environment=settings.environment,
        )


def _clear_session_cookies(response: Response, *, settings: Settings) -> None:
    clear_cookie(response, name=ACCESS_COOKIE, environment=settings.environment)
    clear_cookie(response, name=REFRESH_COOKIE, environment=settings.environment)
    clear_cookie(response, name=OAUTH_PENDING_COOKIE, environment=settings.environment)
    clear_cookie(response, name=API_TOKEN_COOKIE, environment=settings.environment)


def _api_subject(user: AuthUser) -> str | None:
    """Stable owner id for projects: Cognito user id, falling back to email."""

    return user.cognito_user_id or (user.email.strip().lower() if user.email else None)


async def _record_user_login(
    request: Request,
    user: AuthUser,
    subject: str,
    profile: dict[str, Any],
    *,
    license_number: str | None = None,
) -> None:
    """Best-effort persistence of the IC login; never blocks the login flow."""

    database = getattr(request.app.state, "database", None)
    if database is None:
        return
    full_name = user.full_name or " ".join(
        part for part in (user.first_name, user.last_name) if part
    )
    stored_profile = dict(profile)
    if license_number:
        stored_profile["licenseNumber"] = license_number
    try:
        async with database.session() as session:
            repository = PersistenceRepository(session)
            await repository.upsert_user(
                user_id=subject,
                email=user.email,
                full_name=full_name or None,
                phone=user.phone,
                company_name=user.company_name,
                role=user.role,
                pool=user.pool,
                profile=stored_profile,
            )
            await repository.commit()
    except Exception:
        logger.warning("auth_user_record_failed", subject=subject, exc_info=True)


@router.get("/login")
async def login(
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[AuthServiceClient, Depends(get_auth_client)],
) -> RedirectResponse:
    """Start OAuth PKCE — redirect the browser to IC-hosted login."""

    try:
        verifier = generate_code_verifier()
        challenge = code_challenge_s256(verifier)
        # Put verifier in signed `state` so callback works even if the pending
        # cookie is dropped (login host ≠ redirect_uri host).
        state = dump_signed({"code_verifier": verifier}, settings.auth_session_secret)
        authorize_url = client.build_authorize_url(code_challenge=challenge, state=state)
    except ConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    redirect = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    set_cookie(
        redirect,
        name=OAUTH_PENDING_COOKIE,
        value=state,
        max_age=OAUTH_PENDING_MAX_AGE,
        environment=settings.environment,
    )
    return redirect


@router.get("/callback")
async def callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[AuthServiceClient, Depends(get_auth_client)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """Exchange authorization code server-side, set httpOnly cookies, return to frontend."""

    if error:
        return _frontend_redirect(settings, params={"auth": "error", "reason": error})

    if not code or not state:
        return _frontend_redirect(
            settings,
            params={"auth": "error", "reason": "missing_oauth_state"},
        )

    code_verifier = _pending_code_verifier(request, settings, state)
    if not code_verifier:
        return _frontend_redirect(
            settings,
            params={"auth": "error", "reason": "missing_oauth_state"},
        )

    try:
        tokens = await client.exchange_code(code=code, code_verifier=code_verifier)
    except ConfigurationError as exc:
        return _frontend_redirect(settings, params={"auth": "error", "reason": str(exc)})
    except ProviderError as exc:
        return _frontend_redirect(
            settings,
            params={"auth": "error", "reason": exc.args[0] if exc.args else "token_exchange_failed"},
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")
    if not isinstance(access_token, str) or not access_token:
        return _frontend_redirect(
            settings,
            params={"auth": "error", "reason": "missing_access_token"},
        )

    redirect = _frontend_redirect(settings, params={"auth": "success"})
    clear_cookie(redirect, name=OAUTH_PENDING_COOKIE, environment=settings.environment)
    _set_token_cookies(
        redirect,
        settings=settings,
        access_token=access_token,
        refresh_token=refresh_token if isinstance(refresh_token, str) else None,
        expires_in=expires_in if isinstance(expires_in, int) else None,
    )

    # Bridge to the persisted /api/v1 surface: record the login and mint the
    # Launch Kit API JWT so the wizard operates as this IC user (owner_id).
    try:
        profile = await client.me(access_token=access_token)
        user = AuthUser.model_validate(profile)
        subject = _api_subject(user)
        if subject:
            license_number = extract_license_number(profile, access_token=access_token)
            api_token = mint_token(settings, subject, license_number=license_number)
            set_cookie(
                redirect,
                name=API_TOKEN_COOKIE,
                value=api_token.access_token,
                max_age=api_token.expires_in_seconds,
                environment=settings.environment,
            )
            await _record_user_login(
                request,
                user,
                subject,
                dict(profile),
                license_number=license_number,
            )
            logger.info(
                "auth_api_token_bridged",
                subject=subject,
                license_present=bool(license_number),
            )
    except Exception:
        # Login itself succeeded; the wizard will just require a re-login for /api/v1.
        logger.warning("auth_api_token_bridge_failed", exc_info=True)

    return redirect


@router.get("/me", response_model=AuthMeResponse)
async def me(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[AuthServiceClient, Depends(get_auth_client)],
) -> AuthMeResponse:
    """Return the current user profile (or unauthenticated)."""

    access_token = read_cookie(request, ACCESS_COOKIE)
    if not access_token:
        return AuthMeResponse(authenticated=False)

    try:
        profile = await client.me(access_token=access_token)
    except ProviderError as exc:
        if exc.status_code != 401:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        refresh_token = read_cookie(request, REFRESH_COOKIE)
        if not refresh_token:
            return AuthMeResponse(authenticated=False)

        try:
            refreshed = await client.refresh(refresh_token=refresh_token)
            new_access = refreshed.get("accessToken") or refreshed.get("access_token")
            if not isinstance(new_access, str) or not new_access:
                return AuthMeResponse(authenticated=False)
            expires_in = refreshed.get("expiresIn") or refreshed.get("expires_in")
            _set_token_cookies(
                response,
                settings=settings,
                access_token=new_access,
                refresh_token=None,
                expires_in=expires_in if isinstance(expires_in, int) else None,
            )
            profile = await client.me(access_token=new_access)
        except ProviderError:
            return AuthMeResponse(authenticated=False)

    return AuthMeResponse(authenticated=True, user=AuthUser.model_validate(profile))


@router.get("/token", response_model=AuthTokenResponse)
async def api_token(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthTokenResponse:
    """Return a fresh Launch Kit API JWT for the logged-in IC user.

    The SPA stores it and sends it as a Bearer token on /api/v1 requests.
    """

    cookie_token = read_cookie(request, API_TOKEN_COOKIE)
    if not cookie_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    subject = authenticate_token(settings, cookie_token)
    license_number = read_token_license(settings, cookie_token)
    if not license_number:
        database = getattr(request.app.state, "database", None)
        if database is not None:
            try:
                async with database.session() as session:
                    user = await PersistenceRepository(session).get_user(subject)
                    if user is not None and isinstance(user.profile, dict):
                        license_number = extract_license_number(user.profile)
            except Exception:
                logger.warning("auth_token_license_lookup_failed", subject=subject, exc_info=True)
    fresh = mint_token(settings, subject, license_number=license_number)
    set_cookie(
        response,
        name=API_TOKEN_COOKIE,
        value=fresh.access_token,
        max_age=fresh.expires_in_seconds,
        environment=settings.environment,
    )
    return fresh


@router.post("/refresh", response_model=AuthMessageResponse)
async def refresh(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[AuthServiceClient, Depends(get_auth_client)],
) -> AuthMessageResponse:
    refresh_token = read_cookie(request, REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        tokens = await client.refresh(refresh_token=refresh_token)
    except ProviderError as exc:
        _clear_session_cookies(response, settings=settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    access_token = tokens.get("accessToken") or tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Refresh returned no token")

    expires_in = tokens.get("expiresIn") or tokens.get("expires_in")
    _set_token_cookies(
        response,
        settings=settings,
        access_token=access_token,
        refresh_token=None,
        expires_in=expires_in if isinstance(expires_in, int) else None,
    )
    return AuthMessageResponse(message="Session refreshed.")


@router.post("/logout", response_model=AuthMessageResponse)
async def logout(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[AuthServiceClient, Depends(get_auth_client)],
) -> AuthMessageResponse:
    access_token = read_cookie(request, ACCESS_COOKIE)
    refresh_token = read_cookie(request, REFRESH_COOKIE)
    if access_token and refresh_token:
        try:
            await client.revoke_session(access_token=access_token, refresh_token=refresh_token)
        except (ProviderError, ConfigurationError):
            pass
    _clear_session_cookies(response, settings=settings)
    return AuthMessageResponse(message="Successfully logged out.")


@router.get("/logout")
async def logout_redirect(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[AuthServiceClient, Depends(get_auth_client)],
) -> RedirectResponse:
    """RP-initiated logout via IC, after clearing local cookies."""

    access_token = read_cookie(request, ACCESS_COOKIE)
    refresh_token = read_cookie(request, REFRESH_COOKIE)
    if access_token and refresh_token:
        try:
            await client.revoke_session(access_token=access_token, refresh_token=refresh_token)
        except (ProviderError, ConfigurationError):
            pass

    try:
        logout_url = client.build_logout_url()
    except ConfigurationError:
        redirect = _frontend_redirect(settings, params={"auth": "logged_out"})
        _clear_session_cookies(redirect, settings=settings)
        return redirect

    redirect = RedirectResponse(url=logout_url, status_code=status.HTTP_302_FOUND)
    _clear_session_cookies(redirect, settings=settings)
    return redirect
