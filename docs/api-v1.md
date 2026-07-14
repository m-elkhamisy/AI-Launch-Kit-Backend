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
