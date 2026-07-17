# AI Launch Kit — Backend

FastAPI backend for the AI Launch Kit. Serves the API consumed by the frontend.

## Requirements
- Python 3.10+
- pip

## Run locally
```bash
cd ~/Downloads/FINAL/PROJECT
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```
API will be available at http://localhost:8000 (interactive docs at http://localhost:8000/docs).

See `API_CONTRACT.md` for the endpoints the frontend depends on.
