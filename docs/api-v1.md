# API V1

The V1 API is rooted at `/api/v1`. Authentication is temporarily represented by the
server-side `LAUNCHKIT_TESTING_USER_ID`; clients must not send a user ID.

## Implemented project endpoints

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/health` | Returns API status, environment, and contract version. |
| `GET` | `/catalogs/wizard` | Returns authoritative wizard choices and stable IDs. |
| `POST` | `/projects` | Creates a persisted project draft. An empty JSON object uses V1 defaults. |
| `GET` | `/projects/{project_id}` | Returns the current user's complete persisted draft. |
| `PATCH` | `/projects/{project_id}` | Merges supplied business/design fields or replaces `pageLayout`. |
| `POST` | `/projects/{project_id}/profile-extractions` | Validates and stores a multipart profile, then returns a queued operation. |
| `POST` | `/projects/{project_id}/mockups` | Idempotently queues generation of three mockups. |
| `GET` | `/projects/{project_id}/mockups` | Returns the latest generated set. |
| `PUT` | `/projects/{project_id}/selected-mockup` | Persists the chosen mockup. |
| `GET` | `/operations/{operation_id}` | Returns persisted status and safe result/error details. |
| `GET` | `/assets/{asset_id}/content` | Streams an owned asset or sandboxed HTML preview. |

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
