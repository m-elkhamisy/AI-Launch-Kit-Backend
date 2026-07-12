# Main Python Reference

Source: `main` at commit `036b91215fdae6c806a48088c6142b315beffae0`.

This directory preserves the current flat Python/FastAPI behavior before the migration
branch reorganizes it. Treat these files as reference behavior only; they are not the
target architecture.

Included:
- `main.py` - current FastAPI routes and route-embedded orchestration.
- `pipeline.py` - guardrail review, prompt generation, v0 build/status/download, and handoff logic.
- `local_store.py` and `s3_store.py` - current storage implementations and normalization.
- `vercel_deploy.py` - Vercel claim deployment flow.
- `requirements.txt` - current Python dependency list.

