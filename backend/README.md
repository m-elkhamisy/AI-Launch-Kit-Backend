# AI Launch Kit Backend

The production backend is a Python 3.12 package using a src layout. FastAPI is
currently initialized as a transport shell only; business endpoints are deferred
until the callable application capabilities are migrated and verified.

## Local Setup

From the repository root on Windows PowerShell:

```powershell
C:\Users\rabea\AppData\Local\Programs\Python\Python312\python.exe -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
Copy-Item backend\.env.example backend\.env
backend\.venv\Scripts\python.exe -m uvicorn launchkit.main:app --app-dir backend\src --reload
```

The OpenAPI documentation is available at `http://127.0.0.1:8000/docs`. No
business routes are exposed in this migration group.

## Quality Checks

```powershell
backend\.venv\Scripts\python.exe -m ruff format --check backend
backend\.venv\Scripts\python.exe -m ruff check backend
backend\.venv\Scripts\python.exe -m mypy backend\src backend\tests
backend\.venv\Scripts\python.exe -m pytest backend\tests --cov=launchkit --cov-fail-under=90
```

Provider, storage, and deployment environment variables will be documented when
their adapters are migrated. Root-level Python files remain the active legacy
implementation during this phase.

