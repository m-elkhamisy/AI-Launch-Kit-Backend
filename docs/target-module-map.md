# Target Module Map

## Architecture Goal

The target backend should be a modular Python package with FastAPI as a thin
transport layer. Business logic must be callable directly from Python without
HTTP. Existing `main.py` routes are reference behavior only and should not become
the final location for migrated logic.

The package is capability-first: models and business logic live together under
their owning capability (`intake`, `planning`, `generation`, and so on). `core`
contains only genuinely shared technical primitives. Provider-specific HTTP and SDK
code belongs under `adapters`; a separate `domain/application` layer is intentionally
not used.

## Capability Crosswalk

| Capability | main_python | haseeb_typescript | karim_python | Target direction |
|---|---|---|---|---|
| Models and schemas | `main.py` `Submission`; informal dicts | `types/form.ts`, `types/design.ts`, `types/generation.ts` | implicit `answers`, `plan_obj` dicts | Define typed Python models first. |
| Intake normalization | `local_store.py`, `s3_store.py` `normalize_company` | `lib/form-config.ts`, `types/form.ts` | terminal/profile answers | Preserve field mapping and richer Haseeb form schema. |
| Persistence | `local_store.py`, `s3_store.py` | none | local generated files | Storage contract plus local/S3 adapters. |
| Guardrails | `pipeline.py` `review_submission` | fact discipline in prompts, no standalone guardrail | prompt constraints only | Keep explicit model-based review as a capability. |
| Grounding | limited system prompt rules | `lib/grounding.ts` | prompt rules, less structured | Migrate Haseeb fact sheet and anti-hallucination rules. |
| Profile extraction | none | `lib/profile-extraction.ts` | `read_profile_file`, `extract_brief_from_text`, `extract_images_from_file` | Combine Haseeb structured extraction with useful Karim PDF image precedent. |
| Prompt generation | `pipeline.py` `write_brief` | `lib/site-prompts.ts`, `lib/design-utils.ts`, `lib/plan-text.ts` | large prompt blocks in `generate_site.py` | Split by prompt purpose. |
| Mockup generation | none | `generateMockupDesigns`, `fallbackMockup` | `make_mockup`, `fallback_mockup` | Migrate Haseeb staged mockup flow. |
| Site planning | none | `generateSitePlan` | plan generation in CLI | Migrate plan JSON behavior and revision support. |
| Page/section planning | none | `generateSitePlan` in `lib/site-pipeline.ts`; frontend editor state in `lib/page-plan-utils.ts` | plan normalization in CLI; editor helpers are frontend-only | Migrate plan parsing, defaults, home selection, and slug normalization. Keep drag/drop editor state out of the backend. |
| Image sourcing | none | `lib/image-sourcing.ts` | AI image generation and extracted assets | Adapter-based sources with no broken-image fallback. |
| HTML post-processing | none | `lib/html-postprocess.ts` | `fix_ctas`, `strip_breadcrumbs`, `fix_duplicate_images`, `fix_tailwind_classes` | Migrate deterministic repair, include Tailwind class fix if still needed. |
| LLM queueing | none | `lib/request-queue.ts` | parallel executors without shared queue | Shared async request throttle. |
| LLM providers | `pipeline.py` direct `requests` | `lib/openrouter.ts`, `lib/anthropic.ts` | OpenAI client with OpenRouter base URL | Provider adapter layer. |
| v0 integration | `pipeline.py`, `vercel_deploy.py` | `lib/v0.ts` | direct v0 HTTP path | Separate v0 generation/status/download adapter. |
| Deployment | `vercel_deploy.py` | v0 hosting only | CLI zip/share guidance | Keep Vercel claim deployment isolated. |
| Archive/ZIP | `pipeline.py` download zip from v0 | API wrapper zipped built HTML | CLI `shutil.make_archive` | Archive utility only if non-v0 HTML output remains. |
| Orchestration | `main.py`, `pipeline.py` | `lib/site-pipeline.ts` | `generate_site.py` procedural flow | Pipeline coordinates modules only. |

## Proposed Modules

| Module | Responsibility and public callable interface | Models | Sources replaced | Dependencies | Kind, async, tests, compatibility, status |
|---|---|---|---|---|---|
| `launchkit.<capability>.models` | Define Pydantic models beside the capability that owns them: intake, design, planning, generation, profiles, guardrails, storage, and deployment. | Business data only; no HTTP bodies or provider SDK objects. | TS `types/*`, Python route/pipeline result shapes, Karim dict shapes. | `launchkit.core.models` | Pure models; sync; validation/default/alias tests; exact field compatibility where types are known, semantic for informal Python shapes; migrated in group 1, references retained. |
| `launchkit.intake.normalization` | Normalize raw submission mappings: `flatten_submission(raw)`, `normalize_company(raw)`, `missing_required_fields(form)`. | raw mapping, `LegacyCompany`, `OnboardingForm`. | `local_store.py`, `s3_store.py`, `lib/form-config.ts`, `types/form.ts`. | `launchkit.intake.models` | Pure business logic; sync; table-driven alias/nested-raw tests; exact compatibility for existing aliases; migrated in group 1, references retained. |
| `launchkit.storage.contracts` | Storage protocol: `save_submission`, `get_normalized_submission`, `get_raw_submission`, `list_submissions`. | storage records and IDs. | duplicated local/S3 function shapes. | `launchkit.storage.models` | Boundary contract; sync initially; contract tests with fake adapter; semantic compatibility; initial. |
| `launchkit.adapters.local_storage` | JSON-file storage adapter. | storage records. | `local_store.py`. | storage contracts, intake normalization. | External adapter; sync file I/O; temp-dir tests; exact path behavior not required; initial. |
| `launchkit.adapters.s3` | S3 storage adapter. | storage records. | `s3_store.py`. | storage contracts, intake normalization, boto3. | External adapter; sync unless async AWS client adopted later; mocked boto3 tests; semantic compatibility; deferred until local adapter is stable. |
| `launchkit.guardrails` | Review submissions before build: `GuardrailReviewService.review(raw)`. | guardrail result. | `pipeline.py` `review_submission`, prompt safety rules. | text generator contract. | Async coordination; fixed fail-closed parser; provider failures propagate; migrated in stage 6. |
| `launchkit.grounding` | Render the verified fact sheet and expose anti-hallucination rules: `render_fact_sheet(form)` and `FACT_DISCIPLINE`. | onboarding form. | `lib/grounding.ts`, prompt rules in Python/Karim. | intake models | Pure business logic; sync; snapshot tests; exact compatibility with Haseeb wording; migrated in group 2. |
| `launchkit.profiles.extraction` | Extract text/images and fields from uploaded profile files: `ProfileExtractionService.extract(bytes, filename)`. | profile extraction result, extracted images. | `lib/profile-extraction.ts`, Karim file/image helpers. | profile/intake models, injected field extractor and image labeler. | Async coordination with blocking parsing isolated by `to_thread`; tested with TXT/PDF/DOCX fixtures; PDF image extraction intentionally warns; migrated in stage 5. |
| `launchkit.design.tokens` | Resolve palette/font presets and render exact design-token instructions. | design preferences, color swatches, font choices. | `design-utils.ts`, `types/design.ts`. | design models and presets | Pure business logic; sync; preset/custom/AI-choice tests; exact compatibility; migrated in group 2. |
| `launchkit.design.industry` | Resolve the deterministic industry-specific style fallback: `resolve_industry_style_direction(form)`. | onboarding form. | static fallback in `site-prompts.ts`, Karim industry presets. | intake models | Pure business logic; sync; ordered keyword tests; tailored LLM direction remains deferred to an adapter; migrated in group 2. |
| `launchkit.generation.prompts.brief` | Build grounded business/design briefs and the isolated legacy company data block. | form, design, legacy company. | `site-prompts.ts`, `pipeline.py` `BRIEF_TEMPLATE`. | grounding, design | Pure prompt construction; sync; snapshot tests; Haseeb is canonical while conflicting legacy policy stays separate; migrated in group 2. |
| `launchkit.generation.prompts.site` | Build mockup, plan, page, and v0 prompts plus page summaries and exclusion rules. | plan/page models and prompt arguments. | `site-prompts.ts`, Karim prompt blocks. | grounding, planning models | Pure prompt construction; sync; snapshot and rule tests; semantic compatibility with the richer Haseeb flow; migrated in group 2. |
| `launchkit.planning.text` | Render a customer-readable plan summary: `render_plan_text(pages)`. | planned pages. | `plan-text.ts`. | planning models | Pure business logic; sync; exact formatting tests; migrated in group 2. |
| `launchkit.mockups` | Generate design mockups and fallback mockup: `generate_mockups(...)`, `fallback_mockup(...)`. | mockup designs. | `site-pipeline.ts`, Karim mockup flow. | prompts, images, LLM adapter. | Orchestration; async; mocked LLM/image tests plus fallback tests; semantic compatibility; deferred until prompt tests pass. |
| `launchkit.planning.normalization` | Parse model JSON and normalize a site plan: `parse_site_plan(raw)`, `normalize_site_plan(pages)`, and `slugify(value)`. | site plan. | `generateSitePlan` in `site-pipeline.ts`, `plan-text.ts`, Karim plan logic. | planning models/text | Pure transforms; sync; invalid JSON, empty pages, home fallback, defaults, and duplicate slug tests; exact Haseeb compatibility; migrated in stage 4. |
| Haseeb frontend page editor | Page catalog, generated editor IDs, selected/unselected cards, locked Navigation/Footer, and drag/drop transforms. | frontend editor state only. | `page-plan-utils.ts`, frontend generation types. | browser state | Deliberately not migrated. The approved backend plan is already represented by `SitePlan`; API transport can accept that model later without reproducing UI state. |
| `launchkit.images.sourcing` | Resolve planned image specs from uploaded, AI, Pexels, or placeholder sources: `source_images_for_page`, `render_image_catalog`. | sourced images, planned images. | `image-sourcing.ts`, Karim image generation. | models, LLM/image provider, Pexels adapter. | External adapter orchestration; async; mock network/LLM; semantic compatibility; deferred. |
| `launchkit.images.registry` | Replace large data URIs with prompt-safe tokens: `ImageRegistry.compress`, `ImageRegistry.resolve`. | strings/data URLs. | `image-sourcing.ts`. | none | Pure business logic; sync; unit tests for repeated tokens; exact compatibility; initial. |
| `launchkit.html` | Repair generated documents through `repairs.py`, `injections.py`, optional `tailwind.py`, and `processing.py`: `postprocess_html(html, order_page_href, favicon_href=None, normalize_tailwind=False)`. | HTML strings only. | `html-postprocess.ts`, Haseeb `postprocessPage`, Karim repair helpers. | standard-library regex only | Pure deterministic logic; sync; fixture, digest, and composition-order tests; Haseeb behavior is the default while Karim Tailwind snapping is explicit; migrated in group 3. |
| `launchkit.adapters.llm_queue` | Shared request throttle: `RequestQueue.run`, `note_rate_limit`. | queue configuration. | `request-queue.ts`. | asyncio/time | Async coordination with injected clock/sleep tests; migrated in stage 6. |
| `launchkit.adapters.openrouter` | OpenRouter text/JSON/image/profile adapter: `generate_text`, `generate_json`, `generate_image`, `label_image`, `extract_profile_fields`. | normalized results and `ProviderError`. | `openrouter.ts`, `anthropic.ts`, `openrouter-actions.ts`, Python direct requests. | request queue, HTTPX | Async external adapter; retry/cooldown/error behavior covered by mock transport; migrated in stage 6. |
| `launchkit.adapters.v0` | v0 create/init/status/download: `generate_with_v0`, `host_pages_with_v0`, `get_chat_status`, `download_chat_zip`. | v0 result. | `v0.ts`, `pipeline.py` v0 functions. | HTTP client | External adapter; async preferred; mocked HTTP tests for status/404/402; semantic compatibility, preserve pending-on-404; deferred. |
| `launchkit.deployment.claim` | Coordinate claim deployment without provider-specific HTTP details: `claimable_deploy(chat_id, v0, vercel)`. | deployment result. | `vercel_deploy.py`. | v0 and Vercel adapters | Capability coordination; async to match adapters; mocked zip/deploy/transfer tests; semantic compatibility; deferred. |
| `launchkit.archive` | Create zip or single HTML download payloads for built HTML pages if Claude HTML mode remains: `build_site_zip`, `html_download_payload`. | built pages, archive bytes. | Haseeb API `site/zip`, `download-html`, Karim zip creation. | zipfile | Pure/IO utility; sync; unit tests inspect zip contents/filenames; semantic compatibility; deferred. |
| `launchkit.generation.service` | Coordinate capabilities only through `WebsiteGenerationService.generate(request)`. | generation result. | `site-pipeline.ts`, `pipeline.py`, Karim procedural flow. | capability modules and injected adapters | Orchestration; async; integration tests with fake adapters; semantic compatibility; deferred until individual modules are stable. |

## Existing FastAPI Route Classification

These routes in `main.py` are current behavior, not target architecture.

| Route | Current behavior | Classification | Extraction needed |
|---|---|---|---|
| `GET /` | Lists available endpoints. | Temporary reference behavior. | Transport only; likely replaced by health/docs metadata. |
| `POST /submit` | Guardrail review, store raw/normalized data, optionally build with v0. | Future endpoint candidate with embedded business logic. | Extract guardrail, persistence, brief generation, v0 orchestration. |
| `GET /companies` | Lists stored submission IDs. | Future endpoint candidate. | Extract storage listing behind persistence contract. |
| `GET /companies/{company_id}` | Returns normalized and raw submission. | Future endpoint candidate. | Extract storage reads and NotFound mapping. |
| `POST /companies/{company_id}/brief` | Regenerates v0 brief from stored company. | Future endpoint candidate. | Extract brief generation and injection flag handling. |
| `POST /companies/{company_id}/generate` | Regenerates brief and starts v0 build. | Future endpoint candidate with embedded orchestration. | Extract pipeline/v0 adapter use. |
| `GET /builds/{chat_id}` | Polls v0 build status. | Future endpoint candidate. | Extract v0 adapter and HTTP error mapping. |
| `GET /builds/{chat_id}/download` | Downloads generated v0 source zip. | Future endpoint candidate. | Extract v0 zip download adapter. |
| `GET /builds/{chat_id}/handoff` | Returns v0 claim/fork URL. | Later review. | May be superseded by Vercel claim flow. |
| `GET /builds/{chat_id}/claim` | Redirects to v0 handoff URL. | Transport logic needing rewrite. | Keep redirect outside business logic. |
| `POST /builds/{chat_id}/claim-deploy` | Deploys v0 zip to Vercel and creates transfer claim URL. | Future endpoint candidate with external adapter. | Extract Vercel claim deployment. |

## Haseeb Next API Route Behavior

The `origin/haseeb-new-update` `/app/api` route wrappers were inspected but not
imported as reference source because they are framework transport code.

| Route wrapper | Behavior to preserve or document | Imported? |
|---|---|---|
| `site/mockups` | Validates JSON and required form fields, calls `generateMockupDesigns`. | No; behavior covered by models/validation and mockups module. |
| `site/plan` | Requires `chosenMockupHtml`, prepares brief, calls `generateSitePlan`. | No; behavior covered by planning module. |
| `site/build` | Requires non-empty `plan.pages`, calls `runBuild`. | No; behavior covered by pipeline module. |
| `profile` | Multipart `file`, max 15 MB, calls `extractProfile`. | No; validation behavior documented for future transport. |
| `status/[chatId]` | Requires `chatId`, calls `getV0ChatStatus`. | No; covered by v0 adapter. |
| `site/zip` | Creates zip from built HTML pages and slugified filename. | No; preserved as target `archive` behavior. |
| `download-html` | Returns one HTML file download with slugified filename. | No; preserved as target `archive` behavior if needed. |
| `pdf` | React PDF rendering of brief. | No; frontend/reporting concern, defer unless product requires backend PDFs. |

## Main Risks

- `origin/haseeb-new-update` and `origin/karim` have unrelated histories; do not merge them into this branch.
- Local `origin/karim` may disappear after pruning; reference source is now preserved under `reference_implementations/karim_python/`.
- Haseeb's TypeScript logic is richer than current Python; migration should target semantic behavior, not file-for-file translation.
- Current Python `main.py` contains real endpoints, but endpoint redesign is intentionally deferred.
- External calls must be isolated so unit tests never require OpenRouter, v0, Pexels, S3, or Vercel credentials.
