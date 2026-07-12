# Haseeb TypeScript Reference

Source: `origin/haseeb-new-update` at commit `5a067ece85d1a4fa22d6838529949ecd517e6c8d`.

This directory preserves portable TypeScript business logic for migration analysis.
It intentionally does not preserve the Next.js frontend or API route wrappers.

Included:
- `lib/` - prompt builders, pipeline orchestration, grounding, image sourcing,
  HTML repair, profile extraction, request queueing, OpenRouter, v0 integration,
  and related utility logic.
- `types/` - form, design, generation, plan, image, and pipeline result shapes.
- `package*.json`, `tsconfig.json`, and minimal build config - dependency and path-alias context.

Excluded:
- `app/api/` route wrappers. They were inspected and are documented in `docs/target-module-map.md`.
- `components/`, `hooks/`, UI primitives, layout/page/style files, favicon, and browser-only code.

