# API V1

The V1 API is rooted at `/api/v1`. Authentication is temporarily represented by the
server-side `LAUNCHKIT_TESTING_USER_ID`; clients must not send a user ID.

## Implemented project endpoints

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/health` | Returns API status, environment, and contract version. |
| `GET` | `/catalogs/wizard` | Returns authoritative wizard choices and stable IDs. |
| `POST` | `/projects` | Creates a persisted project draft. An empty JSON object uses V1 defaults. |
| `GET` | `/projects` | Lists the current user's project summaries, newest first. |
| `GET` | `/projects/{project_id}` | Returns the current user's complete persisted draft. |
| `PATCH` | `/projects/{project_id}` | Merges supplied business/design fields or replaces `pageLayout`. |
| `POST` | `/projects/{project_id}/profile-extractions` | Validates and stores a multipart profile, then returns a queued operation. |
| `POST` | `/projects/{project_id}/mockups` | Idempotently queues generation of three mockups. |
| `GET` | `/projects/{project_id}/mockups` | Returns the latest generated set. |
| `PUT` | `/projects/{project_id}/selected-mockup` | Persists the chosen mockup. |
| `GET` | `/operations/{operation_id}` | Returns persisted status and safe result/error details. |
| `GET` | `/assets/{asset_id}/content` | Streams an owned asset or sandboxed HTML preview. |
| `POST` | `/projects/{project_id}/builds` | Idempotently queues the final v0 build and returns `202 Accepted`. |
| `GET` | `/builds/{build_id}` | Returns safe build status, URLs, messages, and timestamps. |
| `GET` | `/builds/{build_id}/events` | Streams persisted status events using SSE and `Last-Event-ID`. |
| `GET` | `/builds/{build_id}/download` | Downloads the completed ZIP archive. |
| `POST` | `/builds/{build_id}/deployments` | Idempotently queues a Vercel claim deployment. |
| `GET` | `/deployments/{deployment_id}` | Returns safe deployment and claim status. |
| `POST` | `/webhooks/v0/{token}` | Accepts the configured v0 `message.finished` callback. |
| `POST` | `/webhooks/vercel` | Accepts signed Vercel deployment callbacks. |

Every response uses camel-case JSON fields. Every error uses:

```json
{
  "error": {
    "code": "invalid_input",
    "message": "The request contains invalid values.",
    "details": [],
    "requestId": "req_..."
  }
}
```

The same request ID is returned in `X-Request-ID`. Browser origins are restricted by
the comma-separated `LAUNCHKIT_FRONTEND_ORIGINS` setting.

## Frontend field mapping

| Current frontend field | V1 project field |
|---|---|
| `companyName` | `business.companyName` |
| `uniqueness` | `business.uvp` |
| `customers` | `business.targetAudience` |
| `tagline` | `design.tagline` |
| `cta` | `design.cta` |
| `anythingElse` | `business.notes` |
| Category label | `business.categoryId` from `businessCategories` |
| Mood label | `design.moodId` from `designMoods` |
| Animation index/label | `design.animationId` from `animationLevels` |
| Palette label | `design.paletteId` from `palettes` |
| Font label | `design.fontPairingId` from `fontPairings` |

The API maps the eight frontend mood IDs onto the six existing generation styles.
`minimalist`, `elegant`, `bold`, `playful`, `professional-trustworthy`, `dark-modern`,
`warm-inviting`, and `editorial` remain stable public IDs. Animation IDs map as
`minimal` to static, `low` to subtle, `balanced` to medium, and `high` to rich motion.

Palette colors returned by the API are authoritative. They intentionally replace the
slightly different hard-coded frontend color values.

## Page layout rules

Projects contain one to six selected pages and at most 24 editable sections. Page IDs,
page-template IDs, and slugs must be unique. Section instance IDs must be unique within
their page, and all page and section template IDs must exist in the wizard catalog.

Each page starts with the locked `navigation` section, ends with the locked `footer`
section, and contains at least one editable section between them. Locked state is
validated against the catalog and cannot be changed by the client.

## Profile and mockup operations

Profile extraction accepts PDF, DOCX, PPTX, TXT, Markdown, PNG, and JPEG files up to
`LAUNCHKIT_UPLOAD_MAX_BYTES` (20 MB by default). Extension, MIME type, size, document
structure, and image integrity are validated before persistence. Filenames are reduced
to safe ASCII basenames. Extracted media is stored as project assets; API responses
contain asset metadata and preview URLs, never base64 payloads.

Both profile extraction and mockup generation run through the database-backed worker.
The initiating endpoint returns `202 Accepted`, and the frontend polls the returned
operation at `/operations/{operation_id}`. OpenRouter must be configured before either
operation can be queued. The worker also uses Pexels when configured and selected.

Mockup creation requires `Idempotency-Key`. Repeating a key for the same persisted
draft returns the original operation, while reusing it after changing the draft returns
`409 Conflict`. Generated HTML is stored as an asset and served with a CSP `sandbox`
without `allow-same-origin`; the frontend should render its `previewUrl` in a sandboxed
iframe and must not inject it into the application DOM.

## Final builds

Final builds require a company name, a selected mockup, v0 configuration, and an
`Idempotency-Key`. Only one active build is allowed per project. A repeated key for the
same project revision returns the original build; reusing it after changing the draft
returns `409 Conflict`. The API returns an internal build ID and never exposes the v0
chat or version IDs.

The database-backed worker submits the paid generation once. A transient or uncertain
submission error is failed with a warning and is not submitted automatically again.
After v0 accepts the chat, the worker records the provider reference privately and
reconciles against v0 with exponential backoff until completion, failure, or
`LAUNCHKIT_BUILD_TIMEOUT_SECONDS`. A valid `message.finished` hook wakes reconciliation
early but does not treat the hook payload as authoritative status.

Clients can poll `GET /builds/{build_id}` or subscribe to the SSE endpoint. SSE event IDs
are persisted status-event sequence numbers. Send `Last-Event-ID` after reconnecting to
resume without replaying older events. Completed builds expose `previewUrl`, `webUrl`,
and `downloadUrl`; downloads before completion return `409 Conflict`.

See [`v0-hooks.md`](v0-hooks.md) for hook provisioning, callback security, duplicate
handling, and environment setup.

## Vercel deployments

Deployment creation requires a completed build archive, Vercel configuration, and an
`Idempotency-Key`. The endpoint creates the internal deployment before the worker calls
Vercel. Repeating a key returns the original deployment, and concurrent requests reuse
the active deployment rather than creating another external project.

The worker deploys the stored ZIP, requests an ownership-transfer claim URL, and stores
the Vercel project and deployment IDs only as private provider references. Public API
responses contain the internal deployment ID, status, live URL, claim URL, estimated
24-hour claim expiration, and safe message. The transfer code is exposed only inside
the required Vercel claim URL.

The supported success status is `ready_to_claim`. Vercel does not provide this API with
an authoritative signal that the end user accepted ownership, so the backend does not
fabricate a `completed` transition. Signed `deployment.error` and
`deployment.canceled` callbacks can move a claimable deployment to `failed` or
`cancelled` when Vercel reports a later provider outcome.

Vercel webhooks require `LAUNCHKIT_VERCEL_WEBHOOK_SECRET`. The endpoint computes an
HMAC-SHA1 digest over the unmodified request body and compares it in constant time with
`x-vercel-signature`, following Vercel's documented verification mechanism. Delivery
IDs are persisted for replay protection; unknown deployment IDs are ignored safely.
Configure the Vercel account/team webhook for deployment created, succeeded/ready,
error, and canceled events at `/api/v1/webhooks/vercel`.
