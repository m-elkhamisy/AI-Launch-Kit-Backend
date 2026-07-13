# Repository Guidelines

## Project Structure & Module Organization

Production code uses a root-level src layout under `src/launchkit/`. Organize code
by business capability: `intake/`, `design/`, `planning/`, `generation/`,
`html/`, `profiles/`, `guardrails/`, `storage/`, and `deployment/`. Keep each capability's
models and logic together. Put only genuinely shared configuration, logging,
exceptions, and model configuration in `core/`. Future provider-specific clients
belong in `adapters/`. Tests mirror capabilities under `tests/unit/`; fixed
compatibility inputs belong in `tests/fixtures/`. Architecture and migration status
live in `docs/`.

Treat `reference_implementations/` as read-only source material. Root-level
`main.py`, `pipeline.py`, storage modules, and deployment code are active legacy
files until their behavior is replaced and verified. Do not add new logic there.

## Build, Test, and Development Commands

Create the Python 3.12 environment and install development dependencies:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run the transport shell with `.venv\Scripts\python.exe -m uvicorn
launchkit.main:app --app-dir src --reload`. Run formatting, linting, typing, and
tests with:

```powershell
.venv\Scripts\python.exe -m ruff format --check src tests
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src tests
.venv\Scripts\python.exe -m pytest tests --cov=launchkit --cov-fail-under=90
```

## Coding Style & Naming Conventions

Use complete type annotations on public interfaces and strict mypy-compatible
Python. Name modules and functions with `snake_case`, classes with `PascalCase`, and
enums with uppercase members. Keep modules capability-focused; avoid broad
`utils.py`, `services.py`, or pipeline modules. Business logic must not import
FastAPI or read environment variables directly.

## Testing Guidelines

Use pytest with offline fakes for every external dependency. Add unit tests for
validation and pure behavior, characterization fixtures for preserved behavior,
and equivalence tests where outputs are deterministic. Maintain at least 90% branch
coverage for the migrated package.

## Commit & Pull Request Guidelines

Use focused imperative commits such as `feat: migrate intake normalization`. Pull
requests should identify migrated source files, intentional behavior differences,
quality-check results, configuration changes, and any legacy dependency that
remains. Never commit `.env`, credentials, client uploads, generated sites, or
provider responses containing sensitive data. Keep `.agents/` and `.specify/`
tracked as project workflow scaffolding.
