# Initial Migration Sequence

## Principles

Migrate by capability, not by contributor branch. Keep reference implementations
until replacement behavior is verified. Do not add business API endpoints during
these stages. FastAPI transport redesign comes after the callable Python business
logic is stable.

## Staged Plan

| Stage | Scope | Source files | Proposed target files | Required tests | Mocks | Completion criteria | Depends on | Main risks | Remove reference? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Complete** - typed models and deterministic normalization. | `types/*`, `form-config.ts`, `local_store.py`, `s3_store.py`. | `launchkit/domain/models/*`, `launchkit/application/intake/normalization.py`. | Validation defaults, required fields, alias mapping, nested `raw` flattening. | none | Python models cover known TS/Python inputs and normalization matches current aliases. | none | Rich Haseeb and flat legacy intake remain separate until a lossless mapping is defined. | Keep all references. |
| 2 | Fact grounding and prompt builders. | `grounding.ts`, `site-prompts.ts`, `design-utils.ts`, `plan-text.ts`, `pipeline.py`, Karim prompt blocks. | `launchkit/grounding.py`, `launchkit/prompts/brief.py`, `launchkit/prompts/site.py`. | Snapshot tests for fact sheet, brief, mockup, plan, page, and v0 prompts. | none | Prompt text is deterministic for fixtures and preserves anti-hallucination behavior. | Stage 1 | Prompt wording drift can change generation quality. | Keep references. |
| 3 | HTML post-processing. | `html-postprocess.ts`, Karim `fix_ctas`, `strip_breadcrumbs`, `fix_duplicate_images`, `fix_tailwind_classes`. | `launchkit/html_postprocess.py`. | CTA repair, duplicate image replacement, breadcrumb/nav removal, favicon/AOS injection, optional Tailwind snap tests. | none | Deterministic repairs match intended snippets. | none | Regex differences can over-remove valid nav or miss malformed HTML. | Keep until page build verified. |
| 4 | Plan/page/section transformations. | `page-plan-utils.ts`, `types/generation.ts`, `plan-text.ts`. | `launchkit/planning/site_plan.py`, `launchkit/planning/page_sections.py`. | Slug uniqueness, home fallback, locked Navigation/Footer, add/remove/move/reorder, selected page conversion. | none | Page editor transformations behave like Haseeb reference. | Stage 1 | UI-state concepts may not belong in backend if no API exposes editable plans. | Keep until product flow is confirmed. |
| 5 | Profile extraction. | `profile-extraction.ts`, Karim `read_profile_file`, `extract_images_from_file`, `label_image`. | `launchkit/profile_extraction.py`. | TXT/MD decoding, unsupported extension errors, DOCX text/images fixture, PDF text fixture if dependency chosen, warnings. | LLM image labeler and field extractor. | Extraction returns fields, design hints, images, source filename, warnings without real network calls. | Stages 1-2 | Python dependency choice for DOCX/PDF may change behavior; PDF image extraction needs later decision. | Keep references. |
| 6 | LLM request queue and provider boundary. | `request-queue.ts`, `openrouter.ts`, `anthropic.ts`, Python direct `requests`. | `launchkit/llm/queue.py`, `launchkit/llm/openrouter.py`, `launchkit/llm/contracts.py`. | Retryability, invalid JSON handling, code-fence stripping, rate-limit cooldown behavior. | HTTP client. | All LLM-facing code is behind mockable callables. | Stage 2 | Timing tests can be flaky; avoid real sleeps where possible. | Keep references. |
| 7 | Image sourcing and registry. | `image-sourcing.ts`, Karim image generation. | `launchkit/images/registry.py`, `launchkit/images/sourcing.py`. | Data URI compression/restore, uploaded image rotation, placeholder sentinel, Pexels/AI fallbacks. | Pexels HTTP, image generator. | Every image spec resolves to real source or placeholder panel without broken images. | Stages 1, 6 | Base64 handling can explode prompt size if registry behavior is wrong. | Keep references. |
| 8 | v0 adapter. | `v0.ts`, `pipeline.py` v0 create/status/download/handoff. | `launchkit/v0/adapter.py`. | Create, status pending-on-404, completed/failed mapping, 402 credit error, zip download behavior. | HTTP client. | v0 behavior callable without FastAPI and tested with fake responses. | Stage 6 | SDK vs REST API shape differences; preserve pending-on-404 behavior. | Keep references. |
| 9 | Storage adapters. | `local_store.py`, `s3_store.py`. | `launchkit/persistence/contracts.py`, `launchkit/persistence/local.py`, `launchkit/persistence/s3.py`. | Contract tests for save/get/list/not-found using local temp dir and mocked S3. | boto3/S3. | Local and S3 adapters share one contract and normalization is not duplicated. | Stage 1 | S3 client initialization currently happens at import time; avoid that in target. | Keep references until integration tests pass. |
| 10 | Deployment adapter. | `vercel_deploy.py`. | `launchkit/deployment/vercel_claim.py`. | Zip-to-inline file conversion, project naming, deploy request, transfer code, claim URL. | v0 zip download, Vercel HTTP. | Claim deployment can be tested without Vercel credentials. | Stage 8 | Platform-account billing implications and cleanup policy are product concerns. | Keep reference until product confirms. |
| 11 | Pipeline orchestration. | `site-pipeline.ts`, `pipeline.py`, `generate_site.py`. | `launchkit/pipeline.py`. | End-to-end fake-adapter tests for mockups, plan, Claude HTML, v0-only, both modes, warning propagation. | all external adapters. | Pipeline coordinates capabilities without embedding provider/storage/HTML logic. | Stages 1-10 | Recreating old sequential behavior too literally could preserve accidental coupling. | Keep all references. |
| 12 | FastAPI transport redesign, deferred. | `main.py`, inspected Haseeb `/app/api` wrappers. | later `launchkit_api/*` or equivalent. | Request validation and HTTP error mapping only. | business pipeline fakes. | Thin route layer exists only after business modules are verified. | Stage 11 | Creating endpoints too early will freeze incomplete domain boundaries. | Remove old routes only after replacement is verified. |

## Recommended First Migration Capability

Stage 1 is complete. The next migration group is Stage 2: fact grounding and
deterministic prompt builders. It can now consume canonical intake/design models
without introducing network dependencies.

## Migration Progress

- Backend foundation: Python 3.12 src-layout package, typed settings, structured
  logging, shared exceptions, and a FastAPI shell with no business routes.
- Canonical models: source-backed intake, design, planning, generation, profile,
  image, guardrail, storage, and deployment result shapes.
- Intake normalization: legacy aliases, nested `raw` handling, precedence,
  defaults, and required Haseeb fields covered by fixed characterization tests.
- Verification: Ruff formatting/linting, strict mypy, pytest with at least 90%
  branch coverage, and `git diff --check` are required for every migration commit.
- References: all three directories under `reference_implementations/` remain
  unchanged and are still required for later migration groups.

## Existing Endpoint Review

Do not remove or redesign existing `main.py` routes during the first migration
stages. Treat them as executable reference behavior. Future route work should
only map HTTP payloads to already-tested Python callables and translate domain
errors into HTTP responses.

## Unresolved Decisions

- Whether PDF image extraction from Karim's CLI should be kept, deferred, or
  intentionally dropped in favor of Haseeb's current DOCX-only image extraction.
- Whether backend PDF brief generation is needed; Haseeb's current PDF route is
  React/PDF transport/reporting code, not core business logic.
- Whether the final deployment story should support both v0 handoff and Vercel
  claim deployment, or only one of them.
- Whether editable page/section planning belongs in backend APIs or remains a
  frontend-only planning state transformed before build.
