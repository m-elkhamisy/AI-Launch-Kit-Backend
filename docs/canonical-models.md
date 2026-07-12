# Canonical Model Sources

The backend uses Python snake_case attributes and serializes TypeScript-derived
models with their original camelCase field names. All models reject unknown fields.
The preserved implementations remain the compatibility authority.

| Models | Source | Compatibility and validation |
|---|---|---|
| `OnboardingForm`, `OnboardingField` | `haseeb_typescript/types/form.ts`, `lib/form-config.ts` | Preserves all 21 form keys and empty-string defaults. The five completion requirements are application logic, not constructor requirements. |
| `OnboardingFormPatch` | `ProfileExtractionResult.fields` in `types/generation.ts` | Represents TypeScript `Partial<OnboardingFormData>`; absent fields become `None` and are omitted when requested. |
| `LegacyCompany` | `main_python/local_store.py`, `s3_store.py` | Preserves the 13 normalized snake_case fields and free-form strings. It is intentionally separate from the richer form. |
| `DesignPreferences`, swatches, fonts, enums | `haseeb_typescript/types/design.ts` | Preserves choice values and defaults. Custom IDs require matching custom values; colors must be six-digit hex strings. |
| Planning models | `haseeb_typescript/types/generation.ts` | Preserves `PlannedPageImage`, `PlannedPage`, and `SitePlan`; page caps and editable Navigation/Footer state remain frontend concerns. |
| Generation models | `haseeb_typescript/types/generation.ts` | Preserves mockup, site copy, built page, provider, v0, and pipeline result shapes and ordering. |
| Profile and image models | `types/generation.ts`, `lib/image-sourcing.ts` | Preserves extracted data URLs, profile warnings, design hints, and normalized sourced images. |
| `GuardrailResult` | `main_python/pipeline.py` | Preserves accept/reject values, reason, categories, and empty defaults. |
| Storage models | `main_python/local_store.py`, `s3_store.py` | Preserves `{id, raw, normalized}` and the existing identifier metadata without adding storage-provider fields. |
| `DeploymentResult` | `main_python/vercel_deploy.py` | Preserves claim output names, nullable deployment/live URLs, ready status, and 24-hour expiry text. |

## Intentional Exclusions

- Next.js request/response bodies and root `Submission` are transport models and are
  deferred with endpoint redesign.
- Wizard steps, editable pages/sections, catalog templates, and form rendering config
  are frontend state rather than backend domain data.
- Provider SDK response objects stay behind future adapters.
- Briefs, prompts, and grounded fact sheets remain strings; wrapper models would not
  add validation or domain meaning.
- A legacy-to-rich intake converter is deferred because several mappings are lossy or
  ambiguous and must not be silently combined.

