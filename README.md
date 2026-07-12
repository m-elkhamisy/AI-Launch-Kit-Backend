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
  design/                  Design preference models and rules
  planning/                Site and page planning
  generation/              Generation results and future workflow service
  profiles/                Profile extraction models and logic
  guardrails/              Submission review models and rules
  storage/                 Storage-neutral records and contracts
  deployment/              Deployment and claim behavior
tests/                     Unit tests and characterization fixtures
docs/                      Architecture and migration documentation
reference_implementations/ Preserved Python and TypeScript source material
```

The root-level `main.py`, `pipeline.py`, storage modules, deployment module, and
`requirements.txt` remain the active legacy implementation until equivalent
behavior is verified in `src/launchkit/`.

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

Provider, storage, and deployment configuration will be added as their adapters
are migrated. The next migration group covers fact grounding and deterministic
prompt builders.
