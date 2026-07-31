# AI Launch Kit — Backend

Python backend capabilities and a persisted V1 API for generating multi-page marketing
websites from company intake data. The production package uses a Python 3.12 src layout.

## Requirements
- Python 3.12+
- pip (or `uv`)

- Intake, grounding, guardrails, profile extraction, planning, generation, images,
  HTML repair, archives, storage, and deployment are implemented and tested.
- Business workflows are directly callable without FastAPI or HTTP.
- OpenRouter, Pexels, v0, S3, and Vercel are isolated behind adapters and are tested
  offline with fakes or mock transports.
- FastAPI exposes V1 projects, profile extraction, mockups, builds, SSE, ZIPs, and
  Vercel claim deployments.
- PostgreSQL, Alembic, and a durable database-backed worker provide the workflow foundation.

```text
src/launchkit/             Production package
  api/                     Versioned FastAPI transport, errors, and dependencies
  auth/                    InnovationCity OAuth PKCE login and session cookies
  core/                    Settings, logging, and shared exceptions
  intake/                  Intake models and normalization
  grounding/               Verified fact sheets and factual-discipline rules
  design/                  Design preferences, presets, and token resolution
  planning/                Site plans and customer-readable plan rendering
  projects/                Wizard catalogs, project contracts, and application service
  generation/              Brief, mockup, page-build, and provider-mode orchestration
  images/                  Image sourcing, catalogs, and prompt-safe registry
  html/                    Generated HTML repair and document injections
  profiles/                Profile extraction models and logic
  guardrails/              Submission review models and rules
  storage/                 Local/S3 submission persistence
  deployment/              Deployment and claim behavior
  archive/                 Generated HTML and ZIP downloads
  adapters/                OpenRouter, Pexels, v0, and Vercel HTTP boundaries
tests/                     Unit tests and characterization fixtures
docs/                      Architecture and migration documentation
reference_implementations/ Preserved Python and TypeScript source material
```

## Auth (InnovationCity OAuth PKCE)

Uses InnovationCity `app-auth-service` as the identity provider (IC-hosted license/email
+ OTP login). This backend starts the PKCE flow, exchanges the code server-side, and
stores Cognito tokens in httpOnly cookies. On successful login the backend also mints
a Launch Kit API JWT (same format the `/api/v1` endpoints accept) so the wizard can
call the persisted API as that user.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/login` | Redirect to IC `/authorize` |
| GET | `/auth/callback` | Exchange `code` + PKCE verifier; set cookies; redirect to frontend |
| GET | `/auth/me` | Current user (or `{ authenticated: false }`) |
| GET | `/auth/token` | Launch Kit API JWT for the logged-in IC user |
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
docker compose up -d postgres
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn launchkit.main:app --app-dir src --reload
```

Alternatively, `docker compose up --build` runs PostgreSQL, migrations, the API, and
the durable worker together. Set `LAUNCHKIT_POSTGRES_PORT` when host port 5432 is in use.

For restricted AWS staging through Dokploy, use `docker-compose.dokploy.yml` and
follow [`docs/aws-dokploy-staging.md`](docs/aws-dokploy-staging.md). That topology
keeps PostgreSQL private, runs migrations before application startup, and uses S3 for
shared generated assets.

The OpenAPI documentation is available at `http://127.0.0.1:8000/docs`. See
[`docs/api-v1.md`](docs/api-v1.md) for the implemented contracts and frontend mapping.
See [`docs/v0-hooks.md`](docs/v0-hooks.md) before provisioning an environment callback.
Use [`docs/manual-integration.md`](docs/manual-integration.md) for the credentialed
OpenRouter, v0, storage, and Vercel acceptance run. The decision to retain the old
root transport is recorded in [`docs/legacy-transport.md`](docs/legacy-transport.md).

Legacy root app (older routes):

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

See `API_CONTRACT.md` for the endpoints the frontend depends on.
