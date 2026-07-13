# AI Launch Kit Backend

Python backend capabilities for generating multi-page marketing websites from
company intake data. The production package uses a Python 3.12 src layout. FastAPI
is currently a transport shell only; business endpoints are deferred until the
callable application capabilities are migrated and verified.

## Project Structure

```text
src/launchkit/             Production package
  core/                    Settings, logging, and shared exceptions
  intake/                  Intake models and normalization
  grounding/               Verified fact sheets and factual-discipline rules
  design/                  Design preferences, presets, and token resolution
  planning/                Site plans and customer-readable plan rendering
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

## Local Setup

From the repository root on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.venv\Scripts\python.exe -m uvicorn launchkit.main:app --app-dir src --reload
```

The OpenAPI documentation is available at `http://127.0.0.1:8000/docs`. No
business routes are exposed in the current migration phase.

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

Construct provider adapters with shared `httpx.AsyncClient` instances. OpenRouter,
Pexels, v0, S3, and Vercel credentials are optional at application startup and are
required only when their adapter is constructed or workflow selected. See
`.env.example` for all `LAUNCHKIT_` settings and `docs/api-readiness.md` for the next
transport phase.
