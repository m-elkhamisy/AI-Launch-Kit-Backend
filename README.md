# AI Launch Kit — Backend

FastAPI backend for the AI Launch Kit. Serves the API consumed by the frontend.

## Requirements
- Python 3.12+
- pip (or `uv`)

## Auth (OAuth PKCE)

Uses InnovationCity `app-auth-service` as the identity provider (IC-hosted license/email
+ OTP login). This backend starts the PKCE flow, exchanges the code server-side, and
stores Cognito tokens in httpOnly cookies.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/login` | Redirect to IC `/authorize` |
| GET | `/auth/callback` | Exchange `code` + PKCE verifier; set cookies; redirect to frontend |
| GET | `/auth/me` | Current user (or `{ authenticated: false }`) |
| POST | `/auth/refresh` | Refresh access token cookie |
| POST / GET | `/auth/logout` | Revoke session + clear cookies (GET also hits IC RP logout) |

Required env (see `.env.example`): `LAUNCHKIT_AUTH_CLIENT_ID` (from WeCan),
`LAUNCHKIT_AUTH_REDIRECT_URI` (must match registration exactly),
`LAUNCHKIT_AUTH_BASE_URL`, `LAUNCHKIT_AUTH_FRONTEND_URL`,
`LAUNCHKIT_AUTH_SESSION_SECRET`, `LAUNCHKIT_AUTH_CORS_ORIGINS`.

Registered sandbox callbacks:
- Redirect: `http://localhost:8000/auth/callback`
- Post-logout: `http://localhost:5173/?auth=logged_out`

## Run locally

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Set LAUNCHKIT_AUTH_CLIENT_ID in .env
.venv\Scripts\python.exe -m uvicorn launchkit.main:app --app-dir src --reload --port 8000
```

API is available at http://localhost:8000 (interactive docs at http://localhost:8000/docs).

Legacy root app (older routes):

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

See `API_CONTRACT.md` for the endpoints the frontend depends on.
