import { OnboardingFormData } from "./form";
import { DesignPrefs } from "./design";

/** The three generation modes — this is the single choice that replaced the
 * old "Haseeb engine vs Karim engine" split. It now applies uniformly to
 * one multi-page pipeline instead of picking between two different apps. */
export type GenerationProvider = "v0" | "claude" | "both";

export interface PlannedPageImage {
  section: string;
  desc: string;
}

/** One page in the plan. Names/count/sections are chosen by the model per
 * business (a bakery gets "Menu"; a law firm gets "Practice Areas") instead
 * of a hardcoded 7-page list. */
export interface PlannedPage {
  name: string;
  slug: string;
  isHome: boolean;
  purpose: string;
  sections: string[];
  images: PlannedPageImage[];
}

export interface SitePlan {
  pages: PlannedPage[];
  /** Human-readable rendering used by PlanReview and fed back in as context
   * when the user asks for revisions. */
  raw: string;
}

// ---------------------------------------------------------------------------
// Page & section catalog — powers the "Pick Pages" step (components/
// page-section-manager.tsx). The AI-suggested plan seeds that step (see
// lib/page-plan-utils.ts -> seedEditablePages), but the client can freely
// add/remove pages from this catalog and add/remove/reorder sections on top
// of it, all capped so a plan can never balloon past what one build pass
// can realistically produce.
// ---------------------------------------------------------------------------

/** Every page card always shows a locked Navigation + Footer row. The
 * pipeline attaches both to every page automatically (see navHtml/
 * footerHtml in buildPagePrompt, lib/site-prompts.ts) — they're never part
 * of PlannedPage["sections"], just a fixed visual bookend in the editor. */
export const LOCKED_SECTION_NAMES = ["Navigation", "Footer"] as const;

/** Hard caps for the "Pick Pages" step. MAX_TOTAL_SECTIONS counts the two
 * locked rows (Navigation + Footer) on every SELECTED page, matching what
 * the summary bar under the page cards adds up — not just the custom ones. */
export const MAX_PAGES = 6;
export const MAX_TOTAL_SECTIONS = 17;

export interface PageTemplate {
  id: string;
  name: string;
  /** Marks the one template that's allowed to be the homepage slot. */
  isHomeDefault?: boolean;
  /** Pre-filled the first time this page is added to the plan. */
  defaultSections: string[];
  /** Offered as one-click options from "+ Add section" beyond the defaults. */
  suggestedSections: string[];
}

/** The six starter page types offered in "Pick Pages". Intentionally not
 * exhaustive — anything else (a bakery's "Menu", a law firm's "Practice
 * Areas") comes from the AI-tailored plan itself or the "Custom page…"
 * option, both of which fall back to GENERIC_SUGGESTED_SECTIONS below. */
export const PAGE_CATALOG: PageTemplate[] = [
  {
    id: "home",
    name: "Home",
    isHomeDefault: true,
    defaultSections: ["Hero Section", "Features", "Testimonials", "Call To Action"],
    suggestedSections: ["Stats", "Pricing Preview", "FAQ", "Team Preview", "Gallery Preview", "Logos / Clients", "Newsletter"],
  },
  {
    id: "about",
    name: "About Us",
    defaultSections: ["About Hero", "Our Story", "Team Members", "Values"],
    suggestedSections: ["Mission", "Timeline", "Awards", "Careers CTA", "Stats"],
  },
  {
    id: "services",
    name: "Services",
    defaultSections: ["Services Hero", "Service Cards", "Pricing", "FAQ"],
    suggestedSections: ["Process Steps", "Case Studies", "Comparison Table", "CTA Banner"],
  },
  {
    id: "portfolio",
    name: "Portfolio",
    defaultSections: ["Portfolio Hero", "Gallery", "Case Studies"],
    suggestedSections: ["Filters / Categories", "Client Logos", "Process", "CTA Banner"],
  },
  {
    id: "blog",
    name: "Blog",
    defaultSections: ["Blog Hero", "Blog Posts", "Newsletter"],
    suggestedSections: ["Categories", "Featured Post", "Author Bio"],
  },
  {
    id: "contact",
    name: "Contact",
    defaultSections: ["Contact Hero", "Contact Form", "Map / Location"],
    suggestedSections: ["FAQ", "Office Hours", "Social Links"],
  },
];

/** Offered in "+ Add section" for a page that doesn't match any catalog
 * template above (an AI-tailored page, or a hand-typed custom page) — keeps
 * that control useful even when there's no template to draw suggestions from. */
export const GENERIC_SUGGESTED_SECTIONS = [
  "Overview",
  "Highlights",
  "Details",
  "Gallery",
  "Testimonials",
  "FAQ",
  "Call To Action",
];

/** How many design mockups to generate for the customer to pick from.
 * Reduced from 5 to 3: three visually-distinct directions still give a real
 * choice, while cutting mockup-step latency, token spend, and the size of
 * the parallel burst that was the most 429-prone moment of the pipeline.
 * Lives here (not in the server pipeline) so the wizard button copy and the
 * server-side generation count can never drift apart. */
export const MOCKUP_COUNT = 3;

export interface MockupDesign {
  id: number;
  label: string;
  direction: string;
  html: string;
}

export interface SiteCopy {
  headline: string;
  subheadline: string;
  sections: { heading: string; body: string }[];
  callToAction: string;
}

export interface BuiltPage {
  name: string;
  slug: string;
  filename: string;
  html: string;
}

export interface V0Result {
  chatId: string;
  webUrl: string;
  demoUrl: string | null;
  status: "pending" | "completed" | "failed";
  fileCount: number;
}

export interface PipelineResult {
  provider: GenerationProvider;
  /** Empty when provider === "v0" (v0 owns its own file structure). */
  pages: BuiltPage[];
  siteCopy: SiteCopy | null;
  v0: V0Result | null;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Company-profile upload (PDF / DOCX / TXT / MD -> prefilled brief + photos)
// ---------------------------------------------------------------------------

export interface ExtractedImage {
  filename: string;
  label: string;
  /** base64 data: URI — embedded directly into generated HTML/JSX, no
   * separate file hosting needed. */
  dataUrl: string;
}

export interface ProfileExtractionResult {
  fields: Partial<OnboardingFormData>;
  designHints: Partial<Pick<DesignPrefs, "tagline" | "cta">>;
  images: ExtractedImage[];
  sourceFilename: string;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Wizard steps
// ---------------------------------------------------------------------------

export type WizardStep =
  | "intake"
  | "design"
  | "colors"
  | "mockups"
  | "plan"
  | "building"
  | "results";

export const STEP_ORDER: WizardStep[] = [
  "intake",
  "design",
  "colors",
  "mockups",
  "plan",
  "building",
  "results",
];

// ---------------------------------------------------------------------------
// API request / response bodies
// ---------------------------------------------------------------------------

export interface MockupsRequestBody {
  form: OnboardingFormData;
  design: DesignPrefs;
}
export interface MockupsResponseBody {
  mockups: MockupDesign[];
}

export interface PlanRequestBody {
  form: OnboardingFormData;
  design: DesignPrefs;
  chosenMockupHtml: string;
  feedback?: string;
  previousPlan?: SitePlan;
}
export interface PlanResponseBody {
  plan: SitePlan;
}

export interface BuildRequestBody {
  form: OnboardingFormData;
  design: DesignPrefs;
  provider: GenerationProvider;
  chosenMockupHtml: string;
  plan: SitePlan;
  uploadedImages: ExtractedImage[];
}
export type BuildResponseBody = PipelineResult;

export interface ZipRequestBody {
  companyName: string;
  pages: BuiltPage[];
}
