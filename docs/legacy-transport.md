# Legacy transport retention decision

The root-level `main.py`, `pipeline.py`, storage modules, deployment module, and
legacy `requirements.txt` are intentionally retained for V1.

The canonical runtime is now `launchkit.main:app` with PostgreSQL, Alembic, and
the database-backed worker. Docker, tests, documentation, and the frontend all
use `/api/v1`; no new functionality should be added to the root transport.

Removal is deferred because the repository may still have direct callers of the
old root imports, and a credentialed provider soak has not yet been completed in
staging. Keeping those files does not create a second V1 workflow: they are not
mounted by the V1 router or used by the container entrypoint, and their reusable
behavior has characterized equivalents under `src/launchkit`.

The legacy transport can be removed in a dedicated compatibility release after:

1. The manual integration runbook passes against staging OpenRouter, v0, storage,
   and Vercel credentials.
2. Access logs and repository consumers show no remaining root-route callers.
3. Maintainers announce the import and route removal window.
4. Characterization tests are either retired or moved to permanent V1 coverage.

Until then, security fixes that affect shared behavior must be applied to the
canonical package first and assessed explicitly for legacy callers.
