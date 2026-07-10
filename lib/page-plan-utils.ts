import { renderPlanText } from "@/lib/plan-text";
import { slugify } from "@/lib/utils";
import {
  GENERIC_SUGGESTED_SECTIONS,
  PAGE_CATALOG,
  PageTemplate,
  PlannedPage,
  SitePlan,
} from "@/types/generation";

// ---------------------------------------------------------------------------
// Editable state — what the "Pick Pages" step (components/page-section-
// manager.tsx) actually renders and mutates. Converted to/from SitePlan at
// the edges, so the rest of the pipeline (lib/site-pipeline.ts, the /api/
// site/build route) never has to know this editor exists.
// ---------------------------------------------------------------------------

export interface EditableSection {
  id: string;
  name: string;
  /** Navigation/Footer bookends — always present, never reorderable or
   * removable, and never written into PlannedPage["sections"] (see
   * LOCKED_SECTION_NAMES in types/generation.ts for why). */
  locked?: boolean;
}

export interface EditablePage {
  id: string;
  /** Which PAGE_CATALOG entry this came from, if any — used to look up
   * suggested sections and to hide already-added pages from the catalog
   * quick-add list. Null for AI-tailored or hand-typed custom pages. */
  catalogId: string | null;
  name: string;
  purpose: string;
  isHome: boolean;
  /** Whether this page is actually part of the site right now. Unselected
   * pages stay visible (so the client can see and tune what turning them on
   * would add) but don't count toward MAX_PAGES/MAX_TOTAL_SECTIONS and
   * aren't included when this state is converted back to a SitePlan. */
  selected: boolean;
  sections: EditableSection[];
}

let idCounter = 0;
function genId(prefix: string): string {
  idCounter += 1;
  return `${prefix}-${idCounter}-${Math.random().toString(36).slice(2, 8)}`;
}

function wrapWithLockedBookends(customNames: string[]): EditableSection[] {
  return [
    { id: genId("sec"), name: "Navigation", locked: true },
    ...customNames.map((name) => ({ id: genId("sec"), name })),
    { id: genId("sec"), name: "Footer", locked: true },
  ];
}

export function createPageFromCatalog(template: PageTemplate, isHome = false, selected = true): EditablePage {
  return {
    id: genId("page"),
    catalogId: template.id,
    name: template.name,
    purpose: "",
    isHome,
    selected,
    sections: wrapWithLockedBookends(template.defaultSections),
  };
}

export function createCustomPage(name: string): EditablePage {
  return {
    id: genId("page"),
    catalogId: null,
    name,
    purpose: "",
    isHome: false,
    selected: true,
    sections: wrapWithLockedBookends(["Overview"]),
  };
}

function matchCatalogTemplate(pageName: string): PageTemplate | null {
  const norm = pageName.trim().toLowerCase();
  if (!norm) return null;
  return (
    PAGE_CATALOG.find((t) => t.name.toLowerCase() === norm) ??
    PAGE_CATALOG.find((t) => norm.includes(t.id)) ??
    null
  );
}

/** One AI-planned page -> one editable page, always selected (the AI only
 * ever proposes pages it thinks the site needs) and tagged with a matching
 * catalog id when one exists, purely so "+ Add section" can offer sensible
 * suggestions for it. */
function editablePageFromPlanned(pg: PlannedPage): EditablePage {
  const template = matchCatalogTemplate(pg.name);
  return {
    id: genId("page"),
    catalogId: template?.id ?? null,
    name: pg.name,
    purpose: pg.purpose,
    isHome: pg.isHome,
    selected: true,
    sections: wrapWithLockedBookends(pg.sections),
  };
}

/**
 * Seeds the "Pick Pages" editor from an AI-generated plan: the AI's own
 * pages (kept exactly as it tailored them — a bakery's "Menu" stays "Menu")
 * come in already selected, plus one unselected preview card for every
 * catalog page type the AI *didn't* already cover, so the client can see
 * and toggle on the rest of the standard catalog without losing the
 * AI's tailoring. The homepage always sorts first.
 */
export function seedEditablePages(plan: SitePlan): EditablePage[] {
  const fromPlan = plan.pages.map(editablePageFromPlanned);
  const coveredNames = new Set(fromPlan.map((p) => p.name.trim().toLowerCase()));
  const extras = PAGE_CATALOG.filter((t) => !coveredNames.has(t.name.toLowerCase())).map((t) =>
    createPageFromCatalog(t, false, false)
  );
  const combined = [...fromPlan, ...extras];
  combined.sort((a, b) => Number(b.isHome) - Number(a.isHome));
  // Defensive: guarantee exactly one home if the plan somehow didn't mark one.
  if (combined.length > 0 && !combined.some((p) => p.isHome)) {
    combined[0] = { ...combined[0], isHome: true };
  }
  return combined;
}

/** The inverse of seeding: only SELECTED pages become real PlannedPage
 * entries, and only the unlocked rows of each page become that page's
 * `sections` — the locked Navigation/Footer rows are handled elsewhere in
 * the pipeline (see LOCKED_SECTION_NAMES), so they're intentionally
 * excluded from the data sent to /api/site/build. */
export function planFromEditablePages(pages: EditablePage[]): SitePlan {
  const selected = pages.filter((p) => p.selected);
  const usedSlugs = new Set<string>();
  const plannedPages: PlannedPage[] = selected.map((p) => {
    let slug = p.isHome ? "index" : slugify(p.name);
    const base = slug;
    let k = 2;
    while (usedSlugs.has(slug)) {
      slug = `${base}-${k}`;
      k += 1;
    }
    usedSlugs.add(slug);
    return {
      name: p.name,
      slug,
      isHome: p.isHome,
      purpose: p.purpose,
      sections: p.sections.filter((s) => !s.locked).map((s) => s.name),
      images: [],
    };
  });
  return { pages: plannedPages, raw: renderPlanText(plannedPages) };
}

// ---------------------------------------------------------------------------
// Section-list edits — each returns a new EditablePage, so callers just do
// setPages(prev => prev.map(p => p.id === id ? addSection(p, name) : p)).
// ---------------------------------------------------------------------------

export function addSection(page: EditablePage, name: string): EditablePage {
  const trimmed = name.trim();
  if (!trimmed) return page;
  const footerIndex = page.sections.length - 1;
  const sections = [...page.sections];
  sections.splice(footerIndex, 0, { id: genId("sec"), name: trimmed });
  return { ...page, sections };
}

export function removeSection(page: EditablePage, sectionId: string): EditablePage {
  return { ...page, sections: page.sections.filter((s) => s.id !== sectionId) };
}

export function moveSection(page: EditablePage, sectionId: string, direction: "up" | "down"): EditablePage {
  const sections = [...page.sections];
  const index = sections.findIndex((s) => s.id === sectionId);
  if (index === -1 || sections[index].locked) return page;
  const target = direction === "up" ? index - 1 : index + 1;
  // Index 0 is always Navigation, the last index is always Footer — never
  // move into or past either locked bookend.
  if (target <= 0 || target >= sections.length - 1) return page;
  [sections[index], sections[target]] = [sections[target], sections[index]];
  return { ...page, sections };
}

/** Drag-and-drop reorder: moves `fromId` to just before `toId`. No-ops if
 * either endpoint is a locked row. */
export function reorderSection(page: EditablePage, fromId: string, toId: string): EditablePage {
  if (fromId === toId) return page;
  const sections = [...page.sections];
  const fromIndex = sections.findIndex((s) => s.id === fromId);
  const toIndex = sections.findIndex((s) => s.id === toId);
  if (fromIndex === -1 || toIndex === -1) return page;
  if (sections[fromIndex].locked || sections[toIndex].locked) return page;
  const [moved] = sections.splice(fromIndex, 1);
  const insertAt = sections.findIndex((s) => s.id === toId);
  sections.splice(insertAt, 0, moved);
  return { ...page, sections };
}

/** Suggestions offered by "+ Add section" for a given page — its catalog
 * template's own list when it has one, a generic fallback otherwise, always
 * minus sections it already has. */
export function suggestedSectionsFor(page: EditablePage): string[] {
  const template = page.catalogId ? PAGE_CATALOG.find((t) => t.id === page.catalogId) : null;
  const pool = template ? [...template.defaultSections, ...template.suggestedSections] : GENERIC_SUGGESTED_SECTIONS;
  const existing = new Set(page.sections.filter((s) => !s.locked).map((s) => s.name.toLowerCase()));
  return Array.from(new Set(pool)).filter((name) => !existing.has(name.toLowerCase()));
}
