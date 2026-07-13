# API Readiness

Stages 1-11 are complete. FastAPI remains a route-free transport shell; the next phase
can add endpoints without relocating business rules.

## Callable Workflows

| Future transport action | Existing callable |
|---|---|
| Normalize/store/list/read submissions | `normalize_company`, `SubmissionStore` |
| Review submission safety | `GuardrailReviewService.review` |
| Extract an uploaded profile | `ProfileExtractionService.extract` |
| Generate mockups | `MockupGenerationService.generate` |
| Generate or revise a site plan | `SitePlanningService.generate` |
| Build with Claude, v0, or both | `WebsiteGenerationService.generate` |
| Poll/download/handoff a v0 build | `V0Adapter` lifecycle methods |
| Download generated HTML/ZIP | `html_download_payload`, `build_site_zip` |
| Create a Vercel claim deployment | `ClaimDeploymentService.deploy` |

## Route-Layer Rules

- Construct shared HTTP clients and adapters in application lifespan wiring.
- Translate `DomainError`, `ConfigurationError`, `ProviderError`, and
  `SubmissionNotFound` into HTTP responses; do not raise HTTP exceptions in business code.
- Run synchronous storage methods in synchronous routes or a worker thread.
- Enforce upload size and multipart validation in transport code.
- Keep redirect, content-disposition, and streaming-response behavior in routes.
- Do not expose credentials, raw provider errors, or platform ownership-transfer tokens
  beyond the response fields explicitly required by a workflow.

The root `main.py` routes remain executable legacy behavior until replacement routes pass
transport integration tests. Reference implementations remain read-only.
