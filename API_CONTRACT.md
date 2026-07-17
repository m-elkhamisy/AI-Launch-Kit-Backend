# License-to-Launch — Frontend ↔ Backend API Contract

**Version:** 1.0 · **Base URL (dev):** `http://localhost:8000` · **Docs UI:** `/docs`

This is the contract the frontend conforms to. Field names below are exact — using them
verbatim means zero mapping work on either side.

---

## Conventions

- All request/response bodies are JSON (`Content-Type: application/json`), except
  `/extract` which is `multipart/form-data`.
- **Errors** always return `{"detail": <string or object>}` with an appropriate status:
  `404` not found · `413` file too large · `415` wrong file type · `422` rejected /
  flagged / invalid input · `502` upstream (AI/v0/storage) failure.
- **Auth:** handled by the existing login app (screens 1–2). The backend currently has no
  auth check; when integrating, pass the session/user token in an `Authorization` header —
  the backend will add validation for it in a later step (TODO, owner: backend + auth-app team).
- **CORS:** tell backend the frontend's origin (e.g. `http://localhost:3000`) so it can be
  allow-listed. (TODO once frontend host is known.)

---

## The user flow → endpoint map

| Screen | Action | Endpoint |
|---|---|---|
| 1–2 Login/OTP | existing auth app | — (not this backend) |
| 3 Business form | "Upload here →" (PDF) | `POST /extract` |
| 3–6 all steps | "Review & Generate" (final submit) | `POST /submit` (with `"build": false`) |
| 7 Choose Your Design | on entering the screen | `POST /companies/{id}/previews` |
| 7 Choose Your Design | "Confirm Selection" | `POST /companies/{id}/select-version` |
| 7→8 waiting | progress polling | `GET /builds/{chatId}` |
| 8 Result | "Download source" | `GET /builds/{chatId}/download` |
| 8 Result | "Claim your website" | `POST /builds/{chatId}/claim-deploy` → show `claimUrl` |

---

## 1) `POST /extract` — PDF upload (screen 3, upload path)

`multipart/form-data` with one part named **`file`** (a PDF, ≤ 15 MB).

**200 response** — pre-fill the form with these; the user reviews/edits before submitting:
```json
{
  "fields": {
    "name": "", "industry": "", "tagline": "", "description": "",
    "unique_selling_point": "", "services": [], "audience": "", "tone": "",
    "cta_text": "", "location": "", "website": "",
    "contact_email": "", "contact_phone": "", "extra_context": ""
  }
}
```
Unknown fields come back as `""` — extraction never invents facts.

**Errors:** `415` not a PDF · `413` too large · `422` no extractable text (scanned PDF →
tell the user to fill the form manually) · `422 {"flagged": true, ...}` suspicious content.

---

## 2) `POST /submit` — store the submission (end of screens 3–6)

Send **everything collected across screens 3–6** in one call when the user clicks
*Review & Generate*. Use `"build": false` — in the preview flow, building happens at
`/select-version`, not here.

```json
{
  "data": {
    "name": "Acme Corp",
    "industry": "Tech / SaaS",
    "tagline": "Build faster, ship smarter",
    "description": "…",
    "unique_selling_point": "10 years of expertise, eco-friendly…",
    "services": ["Service A", "Service B"],
    "audience": "Small business owners…",
    "tone": "confident and friendly",
    "cta_text": "Get Started Free",
    "extra_context": "…anything else…",
    "location": "", "website": "",
    "contact_email": "", "contact_phone": "",

    "design_mood": "Dark & Modern",
    "theme_mode": "dark",
    "animation_level": "balanced",

    "colorway": "Modern Blue",
    "font_pairing": "Poppins + Inter",

    "pages": [
      { "name": "Home",     "sections": ["Hero Section", "Features", "Testimonials", "Call To Action"] },
      { "name": "About Us", "sections": ["About Hero", "Our Story", "Team Members", "Values"] },
      { "name": "Contact",  "sections": ["Contact Hero", "Contact Form", "Map / Location"] }
    ]
  },
  "build": false
}
```

**200 response:**
```json
{ "id": "5c23a06…", "accepted": true, "reason": "…", "normalized": { …all fields above… }, "status": "stored" }
```
Keep **`id`** — every later call uses it.

**422 response** (guardrail rejected — show `reason` to the user, nothing was stored):
```json
{ "detail": { "rejected": true, "reason": "…", "categories": ["…"] } }
```

### Field enums / formats

| Field | Values |
|---|---|
| `theme_mode` | `"light"` \| `"dark"` \| `"both"` |
| `animation_level` | `"minimal"` \| `"low"` \| `"balanced"` \| `"high"` |
| `design_mood` | free text from the mood cards (e.g. `"Dark & Modern"`) |
| `colorway` | preset name, free text, or hex — **send the preset's hex values once screen-5 palette specs arrive (TBD)**; e.g. `"Modern Blue (#2563EB primary, #0B1220 dark, #F8FAFC neutral)"` is ideal |
| `font_pairing` | `"<Display Font> + <Body Font>"`, e.g. `"Playfair Display + Source Sans 3"` — must be Google Fonts names |
| `pages[].name` | any of `Home, About Us, Services, Portfolio, Blog, Contact` (or custom) |
| `pages[].sections` | the section labels from the picker, in display order (custom sections allowed) |

---

## 3) `POST /companies/{id}/previews` — 3 homepage previews (screen 7, on entry)

No body. **This call takes minutes** (three homepage builds run concurrently ≈ one build's
duration) — show the "generating designs" state while it runs.

**200 response:**
```json
{
  "companyId": "5c23a06…",
  "previews": [
    { "version": 1, "chatId": "aB1…", "demoUrl": "https://…", "webUrl": "https://v0.app/chat/…", "status": "completed" },
    { "version": 2, "chatId": "cD2…", "demoUrl": "https://…", "webUrl": "…", "status": "completed" },
    { "version": 3, "chatId": "eF3…", "demoUrl": "https://…", "webUrl": "…", "status": "completed" }
  ]
}
```
Render each `demoUrl` in an iframe as the version card. If a preview's `status` is still
`"pending"`, poll `GET /builds/{that chatId}` until it completes.

---

## 4) `POST /companies/{id}/select-version` — build the full site (screen 7, confirm)

```json
{ "version": 2 }
```

**This call takes minutes** (full multi-page build). **200 response:**
```json
{
  "companyId": "5c23a06…",
  "chosenVersion": 2,
  "status": "completed",
  "chatId": "gH4…",
  "demoUrl": "https://…",
  "webUrl": "https://v0.app/chat/…",
  "downloadPath": "/builds/gH4…/download",
  "claimDeployPath": "/builds/gH4…/claim-deploy",
  "poll": "/builds/gH4…"
}
```
The full site keeps the chosen preview's exact design (palette, fonts, hero) expanded to
all requested pages. `404` if `/previews` wasn't called first.

---

## 5) `GET /builds/{chatId}` — poll a build

**200:** `{ "status": "pending" | "completed" | "failed", "webUrl": …, "demoUrl": …, "files": […] }`
Poll every 5–10 s until `completed`. A brief `"note": "…propagating"` while pending is normal.

---

## 6) Delivery (screen 8)

**Download source** — `GET /builds/{chatId}/download` → a ZIP of the full Next.js project
(streamed with `Content-Disposition`; a plain `<a href>` works). *Note: this is a Next.js
project, not standalone HTML — label the button "Download source code".*

**Claim your website** — `POST /builds/{chatId}/claim-deploy` → 
```json
{ "status": "ready_to_claim", "liveUrl": "https://ic-site-….vercel.app", "claimUrl": "https://vercel.com/claim-deployment?code=…", "claimExpires": "24 hours", … }
```
Show `claimUrl` as the claim button (opens Vercel; user clicks *Transfer* and owns the
project). Call once and reuse the URL — each call creates a fresh deployment. The code
expires in 24 h, so trigger this when the user is ready, not preemptively.

Also available: `GET /builds/{chatId}/handoff` (JSON with the v0 page link) and
`GET /builds/{chatId}/claim` (302 redirect to the v0 page).

---

## Open TODOs

1. **Screen-5 values** — palette presets with hex codes + font-pairing list (frontend to send; backend maps verbatim).
2. **Auth integration** — header format + validation once the existing auth app's token scheme is shared.
3. **CORS** — frontend origin(s) to allow-list.
4. **Result-page copy** — rename "Download HTML" → "Download source code"; "Deploy to Domain" → "Claim your website".

---

## Client Documents (brochure + portfolio PDFs) — generated BEFORE the website

Flow position: after `POST /submit` (data stored), before `POST /companies/{id}/previews`.

### POST /companies/{id}/documents
Generates both PDFs from the stored company data. **Idempotent** — returns the existing
documents unless `?force=true`. Errors: 422 `{flagged, reason}` (suspicious input),
502 (generation/render failure).
```json
{ "id": "...", "status": "ready", "regenerated": true,
  "documents": { "brochure":  "/companies/{id}/documents/brochure",
                 "portfolio": "/companies/{id}/documents/portfolio" } }
```

### GET /companies/{id}/documents
Existence check: `{ documents: { brochure: {ready, path}, portfolio: {ready, path} } }`

### GET /companies/{id}/documents/{kind}
Serves the PDF **inline** (`application/pdf`) — usable directly as an `<embed src>` /
`<iframe src>` / new-tab link in the frontend. `kind` = `brochure` | `portfolio`.

Frontend suggestion for the new step: after submit succeeds, call POST documents, show
both PDFs side by side (embed or open-in-tab), with "Continue to website previews"
proceeding to the existing previews step.

---

## Mockup-based previews (architecture change)

Previews are now **Claude-designed HTML hero mockups** served by the backend — not v0 builds.
Cost: ~cents per customer for previews; **one** v0 build total (at select-version).

- `POST /companies/{id}/previews` — generates 3 mockups synchronously (idempotent; `?force=true`
  regenerates). Returns the same contract shape; `demoUrl` now points at this backend.
- `GET  /companies/{id}/previews` — always `completed` once a set exists.
- `GET  /companies/{id}/previews/{version}/html` — serves one mockup as a real page
  (embeddable in iframes — no frame-ancestors restriction).
- `POST /companies/{id}/select-version` — builds the v0 prompt with the CHOSEN MOCKUP'S HTML
  embedded as the design spec and starts the single v0 build. Response shape unchanged.

New env (optional): `MOCKUP_MODEL` — model that designs the mockups
(default = PREVIEW_CONTENT_MODEL; the original script used anthropic/claude-opus-4.8 here).
Ship `hyperui_reference.txt` next to pipeline.py (37 layout blueprints; degrades gracefully if absent).
