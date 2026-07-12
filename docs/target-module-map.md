# Target Module Map

## Architecture Goal

The target backend should be a modular Python package with FastAPI as a thin
transport layer. Business logic must be callable directly from Python without
HTTP. Existing `main.py` routes are reference behavior only and should not become
the final location for migrated logic.

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
| Page/section planning | none | `lib/page-plan-utils.ts`, `PAGE_CATALOG` | `edit_sections`, static page helpers | Migrate Haseeb catalog and transforms. |
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
| `launchkit.models` | Define Pydantic/domain models: `OnboardingForm`, `DesignPreferences`, `SitePlan`, `PlannedPage`, `BuiltPage`, `ExtractedImage`, `PipelineResult`, `StorageRecord`, provider result models. | All request-independent domain models. | TS `types/*`, `main.py` `Submission`, Karim dict shapes. | none | Pure models; sync; unit tests for validation/defaults; exact field compatibility where TS fields are known, semantic for legacy Python; initial. |
| `launchkit.intake.normalization` | Normalize raw submission dicts: `flatten_submission(raw)`, `normalize_company(raw)`, `required_fields_missing(form)`. | raw dict, normalized company/form models. | `local_store.py`, `s3_store.py`, `lib/form-config.ts`, `types/form.ts`. | `launchkit.models` | Pure business logic; sync; table-driven tests for aliases/nested raw; exact compatibility for existing aliases; initial. |
| `launchkit.persistence.contracts` | Storage protocol: `save_submission`, `get_normalized_submission`, `get_raw_submission`, `list_submissions`. | storage records and IDs. | duplicated local/S3 function shapes. | `launchkit.models` | External boundary contract; sync initially; contract tests with fake adapter; semantic compatibility; initial. |
| `launchkit.persistence.local` | JSON-file storage adapter. | storage records. | `local_store.py`. | contracts, normalization. | External adapter; sync file I/O; temp-dir tests; exact path behavior not required; initial. |
| `launchkit.persistence.s3` | S3 storage adapter. | storage records. | `s3_store.py`. | contracts, normalization, boto3. | External adapter; sync unless async AWS client adopted later; mocked boto3 tests; semantic compatibility; deferred until local adapter is stable. |
| `launchkit.guardrails` | Review submissions before build: `review_submission(raw, reviewer) -> GuardrailVerdict`. | guardrail verdict. | `pipeline.py` `review_submission`, prompt safety rules. | LLM provider interface. | Orchestration around adapter; async preferred; tests mock reviewer and parse failures; exact reject-on-unparseable behavior; initial after prompts. |
| `launchkit.grounding` | Render fact sheet and anti-hallucination rules: `render_fact_sheet(form)`, `fact_discipline()`. | onboarding form. | `lib/grounding.ts`, prompt rules in Python/Karim. | models | Pure business logic; sync; snapshot tests; exact compatibility with Haseeb wording where possible; initial. |
| `launchkit.profile_extraction` | Extract text/images and fields from uploaded profile files: `extract_profile(bytes, filename, extractor, image_labeler)`. | profile extraction result, extracted images. | `lib/profile-extraction.ts`, Karim file/image helpers. | models, LLM adapter. | Mixed pure/external; async preferred for LLM labeling; tests with small fixture files and mocked LLM; semantic compatibility; initial after models/prompts. |
| `launchkit.prompts.brief` | Build business brief and design preference text: `build_brief(form, design, industry_direction)`. | form, design. | `site-prompts.ts`, `design-utils.ts`, `pipeline.py` `BRIEF_TEMPLATE`. | grounding, models | Pure prompt construction; sync; snapshot tests; semantic compatibility with richer Haseeb behavior; initial. |
| `launchkit.prompts.site` | Build mockup, plan, page, and v0 prompts: `build_mockup_prompt`, `build_plan_prompt`, `build_page_prompt`, `build_v0_multi_page_brief`. | plan/page/image catalog models. | `site-prompts.ts`, Karim prompt blocks. | grounding, models | Pure prompt construction; sync; snapshot tests; semantic compatibility; initial. |
| `launchkit.mockups` | Generate design mockups and fallback mockup: `generate_mockups(...)`, `fallback_mockup(...)`. | mockup designs. | `site-pipeline.ts`, Karim mockup flow. | prompts, images, LLM adapter. | Orchestration; async; mocked LLM/image tests plus fallback tests; semantic compatibility; deferred until prompt tests pass. |
| `launchkit.planning.site_plan` | Generate/revise site plan and sanitize slugs: `generate_site_plan(...)`, `render_plan_text(...)`. | site plan. | `site-pipeline.ts`, `plan-text.ts`, Karim plan logic. | prompts, LLM adapter, slug utility. | Orchestration plus pure transforms; async; JSON parse and duplicate slug tests; semantic compatibility; initial after prompts. |
| `launchkit.planning.page_sections` | Page catalog and editable plan transforms: `seed_editable_pages`, `plan_from_editable_pages`, section add/remove/move/reorder. | editable page/section, site plan. | `page-plan-utils.ts`, `types/generation.ts`. | models | Pure business logic; sync; unit tests for caps/bookends/reordering; exact compatibility with TS behavior; initial. |
| `launchkit.images.sourcing` | Resolve planned image specs from uploaded, AI, Pexels, or placeholder sources: `source_images_for_page`, `render_image_catalog`. | sourced images, planned images. | `image-sourcing.ts`, Karim image generation. | models, LLM/image provider, Pexels adapter. | External adapter orchestration; async; mock network/LLM; semantic compatibility; deferred. |
| `launchkit.images.registry` | Replace large data URIs with prompt-safe tokens: `ImageRegistry.compress`, `ImageRegistry.resolve`. | strings/data URLs. | `image-sourcing.ts`. | none | Pure business logic; sync; unit tests for repeated tokens; exact compatibility; initial. |
| `launchkit.html_postprocess` | Repair generated HTML: `fix_ctas`, `fix_duplicate_images`, `strip_breadcrumbs`, `inject_aos_failsafe`, `inject_favicon`, optional `fix_tailwind_classes`. | HTML strings. | `html-postprocess.ts`, Karim repair helpers. | none | Pure deterministic logic; sync; unit tests with HTML snippets; exact compatibility for deterministic repairs; initial. |
| `launchkit.llm.queue` | Shared request throttle: `RequestQueue.run`, `note_rate_limit`. | queue config. | `request-queue.ts`. | asyncio/time | External coordination; async; timing-light tests with fake clock where practical; semantic compatibility; initial before adapters. |
| `launchkit.llm.openrouter` | OpenRouter text/JSON/image adapter: `generate_text`, `generate_json`, `generate_image`, `label_image`. | provider responses/errors. | `openrouter.ts`, `anthropic.ts`, `openrouter-actions.ts`, Python direct requests. | queue, http client | External adapter; async preferred; mocked HTTP tests; semantic compatibility; initial after queue. |
| `launchkit.v0.adapter` | v0 create/init/status/download: `generate_with_v0`, `host_pages_with_v0`, `get_chat_status`, `download_chat_zip`. | v0 result. | `v0.ts`, `pipeline.py` v0 functions. | http client | External adapter; async preferred; mocked HTTP tests for status/404/402; semantic compatibility, preserve pending-on-404; deferred. |
| `launchkit.deployment.vercel_claim` | Claim deployment flow: `claimable_deploy(chat_id)`. | deployment result. | `vercel_deploy.py`. | v0 adapter, http client | External adapter; sync or async to match HTTP client; mocked zip/deploy/transfer tests; semantic compatibility; deferred. |
| `launchkit.archive` | Create zip or single HTML download payloads for built HTML pages if Claude HTML mode remains: `build_site_zip`, `html_download_payload`. | built pages, archive bytes. | Haseeb API `site/zip`, `download-html`, Karim zip creation. | zipfile | Pure/IO utility; sync; unit tests inspect zip contents/filenames; semantic compatibility; deferred. |
| `launchkit.pipeline` | Coordinate capabilities only: `prepare_brief`, `generate_mockup_designs`, `generate_site_plan`, `run_build`. | pipeline result. | `site-pipeline.ts`, `pipeline.py`, Karim procedural flow. | all capability modules | Orchestration; async; integration tests with fake adapters; semantic compatibility; deferred until individual modules are stable. |

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

