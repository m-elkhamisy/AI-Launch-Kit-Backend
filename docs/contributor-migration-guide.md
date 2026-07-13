# Contributor Migration Guide

## Purpose

Production code is now organized by capability under `src/launchkit/`. The names
below identify where earlier implementations came from; they do not assign permanent
ownership of the new modules. Everyone should extend the capability module and its
matching tests, not copy logic back into a contributor-specific area.

The preserved inputs under `reference_implementations/` are read-only compatibility
evidence. Root legacy files remain executable only until the replacement API routes
are verified.

## Source Crosswalk

| Earlier implementation | Preserved source | Production replacements |
|---|---|---|
| Anas's Python/FastAPI flow | `reference_implementations/main_python/` | Intake aliases in `intake/normalization.py`; local/S3 persistence in `storage/`; guardrails and legacy brief policy in `guardrails/` and `generation/legacy_*`; v0 in `adapters/v0.py`; Vercel claim flow in `deployment/` and `adapters/vercel.py`; provider-neutral coordination in `generation/service.py`. |
| Haseeb's Next.js/TypeScript flow | `reference_implementations/haseeb_typescript/` | Typed forms and design data in `intake/` and `design/`; grounding in `grounding/`; profile parsing in `profiles/`; prompts and staged generation in `generation/`; plans in `planning/`; images in `images/`; HTML repair in `html/`; queue and providers in `adapters/`. |
| Karim's standalone Python generator | `reference_implementations/karim_python/` | Useful prompt constraints in `generation/prompts/`; profile and image precedents in `profiles/` and `images/`; planning/page-build behavior in `planning/` and `generation/page_builder.py`; deterministic repairs in `html/`; ZIP behavior in `archive/`. |

Haseeb's React components, hooks, API wrappers, PDF component, editable drag/drop
state, and browser-only utilities were intentionally not moved into the backend.
Karim's generated sites, images, and ZIP outputs were also excluded.

### Anas: Root Python Files

| Earlier file | Production location |
|---|---|
| `main.py` | Route behavior remains legacy until Stage 12; reusable coordination moved to the services below. |
| `pipeline.py` guardrails | `guardrails/review.py` and `generation/legacy_prompts.py` |
| `pipeline.py` brief generation | `generation/legacy_brief.py` and `generation/prompts/brief.py` |
| `pipeline.py` v0 lifecycle | `adapters/v0.py` and `archive/building.py` |
| `local_store.py`, `s3_store.py` | `intake/normalization.py` and `storage/{local,s3}.py` |
| `vercel_deploy.py` | `deployment/{archive,claim}.py` and `adapters/vercel.py` |

### Haseeb: TypeScript Business Logic

| Earlier files | Production location |
|---|---|
| `types/form.ts`, `form-config.ts` | `intake/models.py` and `intake/normalization.py` |
| `types/design.ts`, `design-utils.ts` | `design/models.py`, `design/presets.py`, and `design/tokens.py` |
| `grounding.ts` | `grounding/facts.py` and `grounding/rules.py` |
| `profile-extraction.ts` | `profiles/parsing.py`, `profiles/extraction.py`, and `profiles/models.py` |
| `site-prompts.ts`, `plan-text.ts` | `generation/prompts/` and `planning/text.py` |
| `site-pipeline.ts`, generation types | `generation/{briefing,mockups,page_builder,service}.py` and `planning/{normalization,service}.py` |
| `image-sourcing.ts` | `images/{registry,sourcing,catalogs}.py` and `adapters/pexels.py` |
| `html-postprocess.ts` | `html/{repairs,injections,processing}.py` |
| `request-queue.ts`, `openrouter*.ts`, `anthropic.ts` | `adapters/llm_queue.py`, `adapters/openrouter.py`, and provider-neutral contracts in `generation/contracts.py` |
| `v0.ts` | `adapters/v0.py` and generation/deployment result models |
| `page-plan-utils.ts`, `pdf-document.tsx`, `use-google-fonts.ts` | Reference-only frontend/reporting behavior; not backend modules. |

### Karim: Standalone Generator

| Earlier behavior | Production location |
|---|---|
| Profile text and DOCX image extraction | `profiles/parsing.py` and `profiles/extraction.py` |
| Industry direction and prompt constraints | `design/industry.py` and `generation/prompts/` |
| Mockup, plan, and page loops | `generation/mockups.py`, `planning/`, and `generation/page_builder.py` |
| Image generation and fallback handling | `images/` and provider contracts in `generation/contracts.py` |
| CTA, breadcrumb, duplicate-image, and Tailwind repair | `html/`; Tailwind normalization is opt-in. |
| ZIP output | `archive/building.py` |
| `hyperui_reference.txt` | Preserved for later output-quality comparison; not loaded in production. |

## Supported Entry Points

Use capability-level imports in new code:

| Need | Import |
|---|---|
| Normalize legacy intake | `from launchkit.intake import normalize_company` |
| Extract profile data | `from launchkit.profiles import ProfileExtractionService` |
| Review guardrails | `from launchkit.guardrails import GuardrailReviewService` |
| Generate mockups | `from launchkit.generation.mockups import MockupGenerationService` |
| Generate a complete site | `from launchkit.generation import WebsiteGenerationService` |
| Generate or revise a plan | `from launchkit.planning.service import SitePlanningService` |
| Store submissions | `from launchkit.storage import LocalSubmissionStore, S3SubmissionStore` |
| Build downloads | `from launchkit.archive import build_site_zip, html_download_payload` |
| Create claim deployments | `from launchkit.deployment import ClaimDeploymentService` |
| Configure providers | Import the concrete client from `launchkit.adapters.<provider>` |

## Reconciliation Decisions

- Haseeb's grounded fact sheet and richer staged prompts are canonical.
- Anas's legacy brief and guardrail policy remain separate because they have different
  inputs and safety behavior.
- Haseeb's HTML processing order is the default. Karim's Tailwind class snapping is
  available only through the explicit `normalize_tailwind=True` option.
- PDF text extraction is supported; embedded PDF images produce a warning. DOCX text
  and images are supported.
- Provider objects remain inside adapters. Business services accept typed protocols
  and can be tested with fakes.
- Storage and deployment remain separate from website generation.

## Working Agreement

Add logic to the capability that owns the behavior and add tests under the matching
`tests/unit/` directory. Keep FastAPI imports inside `launchkit.main` or the future
`launchkit.api` package. Do not edit reference implementations or add new behavior to
the root legacy modules.
