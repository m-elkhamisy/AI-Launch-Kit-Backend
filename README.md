# LaunchKit Generator

Turn a client brief into a finished, multi-page marketing website. One flow, three ways to generate it.

## What changed in this merge

This used to be two separate engines behind an engine picker — Haseeb's single-page
flow (with the v0 / Claude / Claude+v0 choice) and Karim's multi-page flow (mockups →
plan review → build, ported from a standalone Python script). They're now **one
flow**: Karim's richer mockup → plan → build pipeline, with Haseeb's provider choice
applied across all three generation modes instead of gating two different apps.

Also restored/added:
- **Portfolio upload** — upload a PDF/DOCX/TXT/MD company profile and the form
  prefills itself. DOCX uploads also pull out embedded photos for use as real site
  images (PDF text extraction works; PDF *photo* extraction doesn't yet — see
  `lib/profile-extraction.ts`).
- **Dynamic page planning** — the port had hardcoded a fixed 7-page structure (Home,
  Our Craft, Selections, Story, Reviews, Visit, Order Now) for every business. Plan
  generation now chooses 4–6 page names and sections suited to the actual business
  again, like the original script did.
- **A grounding pass on every prompt** (`lib/grounding.ts`) — the single biggest fix.
  Every prompt that generates copy now gets an explicit fact sheet that separates
  "stated in the brief" from "not provided," plus a standing rule to never invent
  stats, testimonials, team members, addresses, or hours to fill a gap. See below.
- **A much more detailed intake form** — 21 fields across 6 sections instead of 14,
  including a dedicated "Proof & facts" section (real stats/testimonials/team/
  certifications) whose whole point is giving the model something true to work with
  instead of something to guess at.
- **Four image sources** instead of one: your uploaded photos, stock photos (Pexels),
  AI-generated photos, or plain placeholder panels.
- Deterministic HTML repairs ported from the original script
  (`lib/html-postprocess.ts`): dead CTAs always get wired to the real contact page,
  and a repeated image on one page always gets swapped for a styled panel — as a
  backstop, not just a prompt instruction.

## Why the AI was hallucinating, and what actually fixes it

The old prompts said things like *"write real, specific copy, no lorem ipsum"* and
nothing else. That's an instruction to sound specific with no instruction for what to
do when the model doesn't actually have a specific — so it invented one: a founding
year, a client count, a named testimonial. A confident-sounding invented number reads
as "more real" to the model than an honest generic sentence, so without a rule against
it, that's what it reached for.

`lib/grounding.ts` fixes this two ways, applied everywhere copy gets generated
(mockups, plan, page builds, the v0 brief, and profile extraction itself):

1. `renderFactSheet()` turns the brief into sections that are explicitly marked
   either "verified, use as-is" or **"NOT PROVIDED — do not invent."** The model
   isn't left to infer which parts are solid.
2. `FACT_DISCIPLINE` spells out what to do with a gap: omit the claim, write it
   generically, or leave a clearly marked placeholder — never fabricate a plausible
   number, name, date, or quote.

This is necessarily a mitigation, not a guarantee — it's still a language model. Real
stats/testimonials in the "Proof & facts" section make the biggest difference, because
grounding only works if there's something to ground to.

## Generation modes

- **Claude** — every page as clean, self-contained HTML, downloadable/hostable anywhere.
- **v0** — v0 builds the whole multi-page site directly as a live Next.js app, from one
  rich brief written by Claude off the same approved plan and mockup the other modes use.
- **Claude + v0** — Claude writes the HTML, then v0 hosts those exact files (locked, so
  v0 doesn't rewrite them) for an instant shareable link.

## Setup

```bash
npm install
cp .env.example .env.local   # fill in OPENROUTER_API_KEY at minimum
npm run dev
```

See `.env.example` for what each key unlocks — only `OPENROUTER_API_KEY` is required;
everything else degrades gracefully (v0 mode disabled without `V0_API_KEY`, Pexels
falls back to placeholders without `PEXELS_API_KEY`).

## Structure

```
types/            form.ts (intake fields), design.ts (look & feel), generation.ts (pipeline/plan/API types)
lib/
  grounding.ts        fact sheet + anti-hallucination rules — read this first
  form-config.ts       the 21-field intake config
  site-prompts.ts       design system, industry presets, every prompt builder
  site-pipeline.ts      orchestration: mockups, plan, page builds, v0-only build
  image-sourcing.ts     Pexels / AI-generated / uploaded / placeholder
  profile-extraction.ts portfolio upload: text + photo extraction
  html-postprocess.ts   dead-CTA and duplicate-image repair
  anthropic.ts / openrouter.ts / v0.ts    model call wrappers
app/api/
  profile/              portfolio upload
  site/{mockups,plan,build,zip}/
  pdf/ download-html/ status/[chatId]/
components/        site-wizard.tsx is the top-level flow; everything else is one step of it
hooks/             use-site-pipeline.ts (wizard state), use-downloads.ts
```

## Known gaps / next steps

- PDF photo extraction isn't implemented (DOCX is — PDFs need a heavier
  rendering dependency to pull embedded images out).
- No automated tests yet.
- `npm install` / `npm run build` haven't been run in the environment this was
  written in (no Node available) — review the diff, run a build, and fix up
  anything TypeScript flags before shipping.
