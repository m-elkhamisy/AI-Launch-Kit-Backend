# AI Launch Kit Backend

Python backend capabilities and a persisted V1 API for generating multi-page marketing
websites from company intake data. The production package uses a Python 3.12 src layout.

## Current Status

- Intake, grounding, guardrails, profile extraction, planning, generation, images,
  HTML repair, archives, storage, and deployment are implemented and tested.
- Business workflows are directly callable without FastAPI or HTTP.
- OpenRouter, Pexels, v0, S3, and Vercel are isolated behind adapters and are tested
  offline with fakes or mock transports.
- FastAPI exposes V1 projects, profile extraction, mockups, final builds, SSE, and ZIPs.
- PostgreSQL, Alembic, and a durable database-backed worker provide the workflow foundation.

## Project Structure

```text
src/launchkit/             Production package
  api/                     Versioned FastAPI transport, errors, and dependencies
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

The root-level `main.py`, `pipeline.py`, storage modules, deployment module, and
`requirements.txt` remain active legacy transport until replacement API routes are
verified. Their reusable behavior now has tested equivalents under `src/launchkit/`.

## Team Migration Map

| Source work | Where it lives now |
|---|---|
| Anas's Python/FastAPI implementation | `intake/`, `guardrails/`, `storage/`, `generation/legacy_*`, `adapters/v0.py`, and `deployment/` |
| Haseeb's TypeScript/Next.js business logic | `intake/`, `design/`, `grounding/`, `profiles/`, `planning/`, `generation/`, `images/`, `html/`, and `adapters/` |
| Karim's standalone Python generator | Prompt constraints, profile/image handling, planning, page building, HTML repair, and archives in the corresponding capability packages |

See [`docs/contributor-migration-guide.md`](docs/contributor-migration-guide.md) for
the file-level crosswalk, intentional exclusions, compatibility decisions, and
supported imports. Preserved originals remain under `reference_implementations/`.

## Local Setup

From the repository root on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d postgres
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn launchkit.main:app --app-dir src --reload
```

Alternatively, `docker compose up --build` runs PostgreSQL, migrations, the API, and
the durable worker together. Set `LAUNCHKIT_POSTGRES_PORT` when host port 5432 is in use.

The OpenAPI documentation is available at `http://127.0.0.1:8000/docs`. See
[`docs/api-v1.md`](docs/api-v1.md) for the implemented contracts and frontend mapping.
See [`docs/v0-hooks.md`](docs/v0-hooks.md) before provisioning an environment callback.

## Quality Checks

```powershell
.venv\Scripts\python.exe -m ruff format --check src tests
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src tests
.venv\Scripts\python.exe -m pytest tests --cov=launchkit --cov-fail-under=90
```

## Direct Python Usage

Business capabilities do not depend on FastAPI:

```python
from launchkit.intake import normalize_company

company = normalize_company({"businessName": "Northstar", "products": ["Advisory"]})
print(company.model_dump())
```

Grounded prompts are also direct Python callables:

```python
from launchkit.design import DesignPreferences, resolve_industry_style_direction
from launchkit.generation import build_brief
from launchkit.intake import OnboardingForm

form = OnboardingForm(company_name="Northstar", industry="Technology")
brief = build_brief(form, DesignPreferences(), resolve_industry_style_direction(form))
```

Generated HTML can be repaired without invoking a provider:

```python
from launchkit.html import postprocess_html

repaired = postprocess_html(
    generated_html,
    order_page_href="book-a-demo.html",
    favicon_href="/assets/logo.png",
)
```

The complete build workflow is also a direct async Python callable:

```python
from launchkit.generation import WebsiteGenerationRequest, WebsiteGenerationService

service = WebsiteGenerationService(
    brief_service=brief_service,
    page_builder=page_builder,
    copy_extractor=copy_extractor,
    image_catalogs=image_catalogs,
    v0=v0_adapter,  # optional for Claude-only generation
)
result = await service.generate(WebsiteGenerationRequest(...))
```

The primary service entry points are:

```python
from launchkit.deployment import ClaimDeploymentService
from launchkit.generation import WebsiteGenerationService
from launchkit.generation.mockups import MockupGenerationService
from launchkit.guardrails import GuardrailReviewService
from launchkit.planning.service import SitePlanningService
from launchkit.profiles import ProfileExtractionService
```

Construct provider adapters with shared `httpx.AsyncClient` instances. OpenRouter,
Pexels, v0, S3, and Vercel credentials are optional at application startup and are
required only when their adapter is constructed or workflow selected. See
`.env.example` for all `LAUNCHKIT_` settings and `docs/api-readiness.md` for the next
transport phase.
