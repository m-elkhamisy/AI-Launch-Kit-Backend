# Initial Migration Sequence

## Principles

Migrate by capability, not by contributor branch. Keep reference implementations
until replacement behavior is verified. Do not add business API endpoints during
these stages. FastAPI transport redesign comes after the callable Python business
logic is stable.

## Staged Plan

| Stage | Scope | Source files | Proposed target files | Required tests | Mocks | Completion criteria | Depends on | Main risks | Remove reference? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Complete** - typed models and deterministic normalization. | `types/*`, `form-config.ts`, `local_store.py`, `s3_store.py`. | Capability `models.py` files and `launchkit/intake/normalization.py`. | Validation defaults, required fields, alias mapping, nested `raw` flattening. | none | Python models cover known TS/Python inputs and normalization matches current aliases. | none | Rich Haseeb and flat legacy intake remain separate until a lossless mapping is defined. | Keep all references. |
| 2 | **Complete** - fact grounding and prompt builders. | `grounding.ts`, `site-prompts.ts`, `design-utils.ts`, `plan-text.ts`, `pipeline.py`, Karim prompt blocks. | `launchkit/grounding/`, `launchkit/design/{presets,tokens,industry}.py`, `launchkit/planning/text.py`, `launchkit/generation/prompts/`. | Fact-sheet fixture, design-token equivalence, prompt rule assertions, and full-output digest snapshots. | none | Prompt text is deterministic for fixtures and preserves anti-hallucination behavior. | Stage 1 | Prompt wording drift can change generation quality. | Keep references. |
| 3 | **Complete** - HTML post-processing. | `html-postprocess.ts`, Haseeb `postprocessPage`, Karim `fix_ctas`, `strip_breadcrumbs`, `fix_duplicate_images`, `fix_tailwind_classes`. | `launchkit/html/{repairs,injections,tailwind,processing}.py`. | CTA repair, duplicate image replacement, breadcrumb/nav removal, favicon/AOS injection, composition order, output digest, and opt-in Tailwind snapping. | none | Deterministic repairs match intended snippets and are callable without orchestration. | none | Regex differences can over-remove valid nav or miss malformed HTML; Tailwind snapping remains opt-in. | Keep until page build verified. |
| 4 | Plan parsing and normalization. | `generateSitePlan` in `site-pipeline.ts`, `types/generation.ts`, `plan-text.ts`. `page-plan-utils.ts` is retained only as frontend reference. | `launchkit/planning/normalization.py`. | Invalid/empty JSON, code fences, slug uniqueness, home fallback, field defaults, and page ordering. | none | Model output becomes a canonical `SitePlan` with exactly one home page and deterministic slugs. | Stage 1 | Model output can be malformed; fail clearly instead of inventing pages. Frontend editor state must not leak into backend models. | Keep all references. |
| 5 | Profile extraction. | `profile-extraction.ts`, Karim `read_profile_file`, `extract_images_from_file`, `label_image`. | `launchkit/profiles/extraction.py`. | TXT/MD decoding, unsupported extension errors, DOCX text/images fixture, PDF text fixture if dependency chosen, warnings. | LLM image labeler and field extractor. | Extraction returns fields, design hints, images, source filename, warnings without real network calls. | Stages 1-2 | Python dependency choice for DOCX/PDF may change behavior; PDF image extraction needs later decision. | Keep references. |
| 6 | LLM request queue and provider boundary. | `request-queue.ts`, `openrouter.ts`, `anthropic.ts`, Python direct `requests`. | `launchkit/adapters/llm_queue.py`, `launchkit/adapters/openrouter.py`. | Retryability, invalid JSON handling, code-fence stripping, rate-limit cooldown behavior. | HTTP client. | All LLM-facing code is behind mockable callables. | Stage 2 | Timing tests can be flaky; avoid real sleeps where possible. | Keep references. |
| 7 | Image sourcing and registry. | `image-sourcing.ts`, Karim image generation. | `launchkit/images/registry.py`, `launchkit/images/sourcing.py`. | Data URI compression/restore, uploaded image rotation, placeholder sentinel, Pexels/AI fallbacks. | Pexels HTTP, image generator. | Every image spec resolves to real source or placeholder panel without broken images. | Stages 1, 6 | Base64 handling can explode prompt size if registry behavior is wrong. | Keep references. |
| 8 | v0 adapter. | `v0.ts`, `pipeline.py` v0 create/status/download/handoff. | `launchkit/adapters/v0.py`. | Create, status pending-on-404, completed/failed mapping, 402 credit error, zip download behavior. | HTTP client. | v0 behavior callable without FastAPI and tested with fake responses. | Stage 6 | SDK vs REST API shape differences; preserve pending-on-404 behavior. | Keep references. |
| 9 | Storage adapters. | `local_store.py`, `s3_store.py`. | `launchkit/storage/contracts.py`, `launchkit/adapters/local_storage.py`, `launchkit/adapters/s3.py`. | Contract tests for save/get/list/not-found using local temp dir and mocked S3. | boto3/S3. | Local and S3 adapters share one contract and normalization is not duplicated. | Stage 1 | S3 client initialization currently happens at import time; avoid that in target. | Keep references until integration tests pass. |
| 10 | Deployment adapter. | `vercel_deploy.py`. | `launchkit/deployment/claim.py`, `launchkit/adapters/vercel.py`. | Zip-to-inline file conversion, project naming, deploy request, transfer code, claim URL. | v0 zip download, Vercel HTTP. | Claim deployment can be tested without Vercel credentials. | Stage 8 | Platform-account billing implications and cleanup policy are product concerns. | Keep reference until product confirms. |
| 11 | Pipeline orchestration. | `site-pipeline.ts`, `pipeline.py`, `generate_site.py`. | `launchkit/generation/service.py`. | End-to-end fake-adapter tests for mockups, plan, Claude HTML, v0-only, both modes, warning propagation. | all external adapters. | Service coordinates capabilities without embedding provider/storage/HTML logic. | Stages 1-10 | Recreating old sequential behavior too literally could preserve accidental coupling. | Keep all references. |
| 12 | FastAPI transport redesign, deferred. | `main.py`, inspected Haseeb `/app/api` wrappers. | later `launchkit/api/*`. | Request validation and HTTP error mapping only. | generation service fakes. | Thin route layer exists only after business modules are verified. | Stage 11 | Creating endpoints too early will freeze incomplete capability boundaries. | Remove old routes only after replacement is verified. |

## Recommended Next Migration Capability

Stages 1 through 3 are complete. The next migration group is Stage 4: deterministic
plan, page, and section transformations. It can establish slug, homepage, section
ordering, and editable-plan behavior without adding provider or HTTP dependencies.

## Migration Progress

- Backend foundation: Python 3.12 src-layout package, typed settings, structured
  logging, shared exceptions, and a FastAPI shell with no business routes.
- Canonical models: source-backed intake, design, planning, generation, profile,
  image, guardrail, storage, and deployment result shapes.
- Intake normalization: legacy aliases, nested `raw` handling, precedence,
  defaults, and required Haseeb fields covered by fixed characterization tests.
- Grounding and prompts: Haseeb fact-sheet discipline, exact palette/font preset
  resolution, ordered static industry fallback, plan rendering, and mockup, plan,
  page, and v0 prompt builders are callable without FastAPI or network access.
- Compatibility: the root `BRIEF_TEMPLATE` data message is available separately
  from the canonical grounded brief. Karim's overlapping page/CTA/SEO constraints
  are represented by the richer Haseeb builders rather than a contributor-specific
  duplicate.
- HTML processing: CTA wiring, duplicate-image replacement, breadcrumb and duplicate
  navigation removal, favicon injection, and the AOS visibility fallback preserve the
  Haseeb processing order. Karim's numeric Tailwind normalization is available only
  through `normalize_tailwind=True` so it cannot silently rewrite newer output.
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
- Whether Karim's optional HyperUI blueprint and extra section-pattern prompt pack
  should augment the canonical design contract after output-quality comparison.
- The model-written industry direction and root legacy v0 system prompt remain with
  the future LLM adapter stage. Their provider behavior and conflicting personal-data
  policy must be tested before either is connected to canonical prompts.
- Karim's AOS fallback also retries Lucide icon initialization, while Haseeb's later
  implementation does not. The canonical fallback follows Haseeb; Lucide lifecycle
  handling remains available in the Karim reference for generator-adapter review.
