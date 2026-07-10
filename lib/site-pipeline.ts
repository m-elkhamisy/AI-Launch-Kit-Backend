import { OnboardingFormData } from "@/types/form";
import { DesignPrefs } from "@/types/design";
import {
  BuiltPage,
  ExtractedImage,
  GenerationProvider,
  MOCKUP_COUNT,
  MockupDesign,
  PipelineResult,
  PlannedPage,
  PlannedPageImage,
  SitePlan,
  V0Result,
} from "@/types/generation";
import { slugify, mapWithConcurrency } from "@/lib/utils";
import { callClaude, extractSiteCopy, generateHtmlPage, htmlLooksComplete } from "@/lib/anthropic";
import { stripCodeFence } from "@/lib/openrouter";
import {
  buildBrief,
  buildForbiddenSections,
  buildMockupPrompt,
  buildPagePrompt,
  buildPageSummary,
  buildPlanPrompt,
  buildV0MultiPageBrief,
  getIndustryStyleDirection,
  renderPlanText,
} from "@/lib/site-prompts";
import {
  createImageRegistry,
  ImageRegistry,
  isRealImage,
  renderImageCatalog,
  sourceImagesForPage,
} from "@/lib/image-sourcing";
import {
  fixCtas,
  fixDuplicateImages,
  injectAosFailsafe,
  injectFavicon,
  stripBreadcrumbs,
} from "@/lib/html-postprocess";
import { generateWithV0, hostMultiPageWithV0, isV0Configured } from "@/lib/v0";

const MOCKUP_DIRECTIONS: Array<{ label: string; direction: string }> = [
  { label: "Editorial & elegant", direction: "Direction A: editorial & elegant — large serif headlines, lots of whitespace, refined." },
  { label: "Bold & modern", direction: "Direction B: bold & modern — big type, strong color blocks, confident and punchy." },
  { label: "Sleek & premium dark", direction: "Direction C: sleek & premium dark — dark background, glowing accents, high-end tech feel." },
  { label: "Warm & organic", direction: "Direction D: warm & organic — soft tones, rounded shapes, friendly and inviting." },
  { label: "Clean & minimal", direction: "Direction E: clean & minimal — restrained palette, precise grid, lots of air." },
];

/** The first MOCKUP_COUNT directions are the most visually distinct trio —
 * the two dropped ones ("Warm & organic", "Clean & minimal") overlapped the
 * most with the editorial direction in practice. */
const ACTIVE_MOCKUP_DIRECTIONS = MOCKUP_DIRECTIONS.slice(0, MOCKUP_COUNT);

// -----------------------------------------------------------------------
// Guaranteed-render fallback mockup — used only if the AI mockup for a
// direction comes back invalid twice. A design tile the customer can't see
// is worse than a plain one, so this never fails and needs no network.
// -----------------------------------------------------------------------

const FALLBACK_PALETTES: Array<{ bg: string; accent: string; fg: string }> = [
  { bg: "#0B1020", accent: "#00C2FF", fg: "#FFFFFF" },
  { bg: "#FAF4EC", accent: "#C9A24B", fg: "#2B1D14" },
  { bg: "#101418", accent: "#7C4DFF", fg: "#F5F5F5" },
  { bg: "#F7F7F5", accent: "#1E4080", fg: "#15181D" },
  { bg: "#141414", accent: "#E8C4B8", fg: "#FAFAF7" },
];

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Exported for tests — production code only reaches it through
 * generateMockupDesigns when a direction fails twice. */
export function fallbackMockup(
  index: number,
  form: OnboardingFormData,
  design: DesignPrefs,
  previewImageUrl: string | null
): string {
  const { bg, accent, fg } = FALLBACK_PALETTES[index % FALLBACK_PALETTES.length];
  const company = escapeHtml(form.companyName || "Your company");
  const industry = escapeHtml(form.industry || "");
  const headline = escapeHtml(design.tagline?.trim() || form.companyName || "Your company");
  const subline = escapeHtml(
    `${form.businessActivity || form.industry || "What we do"} — built for ${form.targetAudience || "your customers"}.`
  );
  const cta = escapeHtml(design.cta?.trim() || "Get in touch");
  const imgTag = previewImageUrl
    ? `<img src="${previewImageUrl}" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.25">`
    : "";
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${company}</title></head>
<body style="margin:0;background:${bg};color:${fg};font-family:system-ui">
<nav style="display:flex;justify-content:space-between;align-items:center;padding:18px 40px;border-bottom:1px solid ${accent}33">
 <strong style="letter-spacing:.05em">${company}</strong>
 <span><a href="#" style="color:${fg};margin-right:22px;text-decoration:none">About</a>
 <a href="#" style="background:${accent};color:${bg};padding:10px 18px;border-radius:10px;text-decoration:none">${cta}</a></span></nav>
<section style="position:relative;min-height:620px;display:flex;align-items:center;overflow:hidden">
 ${imgTag}
 <div style="position:relative;max-width:640px;padding:60px 40px">
  <div style="color:${accent};letter-spacing:.15em;font-size:12px;text-transform:uppercase;margin-bottom:14px">${industry}</div>
  <h1 style="font-size:56px;line-height:1.1;margin:0 0 18px">${headline}</h1>
  <p style="opacity:.85;line-height:1.6;margin:0 0 26px">${subline}</p>
  <a href="#" style="background:${accent};color:${bg};padding:14px 26px;border-radius:12px;text-decoration:none;font-weight:600">${cta}</a>
 </div></section></body></html>`;
}

const ORDER_KEYWORDS = ["order", "contact", "book", "reserve", "visit", "get in touch", "enquir", "inquir"];

function findOrderPage(pages: PlannedPage[]): PlannedPage {
  const found = pages.find((p) => ORDER_KEYWORDS.some((w) => p.name.toLowerCase().includes(w)));
  return found ?? pages[pages.length - 1];
}

function extractShell(html: string): { nav: string; footer: string } {
  const navMatch = html.match(/<nav\b[\s\S]*?<\/nav>/i);
  const footerMatch = html.match(/<footer\b[\s\S]*?<\/footer>/i);
  return { nav: navMatch?.[0] ?? "", footer: footerMatch?.[0] ?? "" };
}

/** Computed once per API call (not once per page) — every page in one build
 * shares the same brief so an industry direction isn't re-rolled per page. */
export async function prepareBrief(form: OnboardingFormData, design: DesignPrefs): Promise<string> {
  const direction = await getIndustryStyleDirection(form);
  return buildBrief(form, design, direction);
}

export async function generateMockupDesigns(
  form: OnboardingFormData,
  design: DesignPrefs,
  uploadedImages: ExtractedImage[]
): Promise<{ mockups: MockupDesign[]; brief: string }> {
  const brief = await prepareBrief(form, design);

  // one shared, on-topic preview image so all the mockups look coherent
  // instead of unrelated (or missing) hero photos
  let previewImageUrl: string | null = null;
  if (design.imageSource !== "placeholder") {
    const [sourced] = await sourceImagesForPage(
      [
        {
          section: "hero",
          desc: `A professional, appealing hero photo representing this business: ${form.industry} (${form.companyName})`,
        },
      ],
      {
        imageSource: design.imageSource,
        industry: form.industry,
        companyName: form.companyName,
        uploaded: uploadedImages,
        uploadedOffset: 0,
      }
    );
    if (sourced && isRealImage(sourced.src)) previewImageUrl = sourced.src;
  }

  // The prompt only ever sees a short __IMG_REF_n__ token for this photo —
  // never the raw base64 — since a single uploaded/AI image alone can be
  // hundreds of thousands of tokens as literal text. registry.resolve()
  // below swaps the real src back in once the model has echoed the token.
  const registry = createImageRegistry();
  const promptPreviewImageUrl = previewImageUrl ? registry.compress(previewImageUrl) : null;

  // Parallel in shape, paced underneath: every generateHtmlPage attempt
  // flows through the shared OpenRouter queue, so this can't burst past the
  // key's rate limit no matter what MOCKUP_COUNT is set to.
  const mockups = await Promise.all(
    ACTIVE_MOCKUP_DIRECTIONS.map(async (d, i): Promise<MockupDesign> => {
      const prompt = buildMockupPrompt(d.direction, brief, promptPreviewImageUrl);
      let html: string | null = null;
      try {
        // generateHtmlPage already retries once internally when the output
        // is incomplete — so an invalid result here means it failed twice.
        html = await generateHtmlPage(prompt, { maxTokens: 6000 });
        html = registry.resolve(html);
      } catch (err) {
        console.warn(
          `Mockup "${d.label}" failed to generate (${err instanceof Error ? err.message : String(err)}) — using the guaranteed fallback design.`
        );
      }
      if (!html || !htmlLooksComplete(html)) {
        if (html) {
          console.warn(`Mockup "${d.label}" came back incomplete twice — using the guaranteed fallback design.`);
        }
        html = fallbackMockup(i, form, design, previewImageUrl);
      }
      return { id: i + 1, label: d.label, direction: d.direction, html };
    })
  );

  return { mockups, brief };
}

export async function generateSitePlan(
  brief: string,
  chosenMockupHtml: string,
  feedback?: string,
  previousPlan?: SitePlan
): Promise<SitePlan> {
  // chosenMockupHtml round-trips through the browser and arrives here with
  // whatever base64 image data the mockup step baked into it — compress
  // before it's pasted into the prompt. The plan's response is JSON with no
  // src fields, so there's nothing to resolve() back afterward.
  const prompt = buildPlanPrompt(brief, createImageRegistry().compress(chosenMockupHtml), feedback, previousPlan);
  const raw = await callClaude(prompt, { maxTokens: 2500 });
  const cleaned = stripCodeFence(raw);

  let parsed: { pages: Array<Partial<PlannedPage>> };
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    throw new Error("The planning step returned invalid JSON — please try again.");
  }
  if (!parsed.pages || parsed.pages.length === 0) {
    throw new Error("The planning step didn't return any pages — please try again.");
  }

  const homeIndex = parsed.pages.findIndex((p) => p.isHome);
  const resolvedHomeIndex = homeIndex === -1 ? 0 : homeIndex;

  const usedSlugs = new Set<string>();
  const pages: PlannedPage[] = parsed.pages.map((p, i) => {
    const isHome = i === resolvedHomeIndex;
    let slug = isHome ? "index" : slugify(p.name || `page-${i + 1}`);
    const base = slug;
    let k = 2;
    while (usedSlugs.has(slug)) {
      slug = `${base}-${k}`;
      k++;
    }
    usedSlugs.add(slug);
    return {
      name: p.name || `Page ${i + 1}`,
      slug,
      isHome,
      purpose: p.purpose || "",
      sections: p.sections && p.sections.length ? p.sections : ["Overview"],
      images: p.images || [],
    };
  });

  return { pages, raw: renderPlanText(pages) };
}

async function buildImageCatalogs(
  form: OnboardingFormData,
  design: DesignPrefs,
  plan: SitePlan,
  uploadedImages: ExtractedImage[],
  registry?: ImageRegistry
): Promise<Record<string, string>> {
  let uploadedOffset = 0;
  const catalogs: Record<string, string> = {};
  for (const pg of plan.pages) {
    // Guarantee: when the person asked for real photos, every page gets at
    // least one image spec even if the plan omitted them — otherwise a page
    // silently ships photo-less because of a planning-step JSON gap, which
    // reads as a bug to the customer. Placeholder mode keeps the plan as-is.
    const specs: PlannedPageImage[] =
      design.imageSource !== "placeholder" && pg.images.length === 0
        ? [
            {
              section: pg.sections[0] ?? "main section",
              desc: `${form.industry} — photo for the ${pg.name} page (${pg.sections[0] ?? "main section"})`,
            },
          ]
        : pg.images;

    const sourced = await sourceImagesForPage(specs, {
      imageSource: design.imageSource,
      industry: form.industry,
      companyName: form.companyName,
      uploaded: uploadedImages,
      uploadedOffset,
    });
    uploadedOffset += specs.length;
    catalogs[pg.name] = renderImageCatalog(sourced, registry);
  }
  return catalogs;
}

/** The client's own logo (if their profile upload contained one) becomes the
 * favicon on every page — same behavior as the original tool. */
function findLogoDataUrl(uploadedImages: ExtractedImage[]): string | null {
  const logo = uploadedImages.find((img) => img.label.toLowerCase().includes("logo"));
  return logo?.dataUrl ?? null;
}

/** Shared cleanup every built page goes through, in the original tool's
 * order: repair CTAs, de-duplicate images, strip stray breadcrumbs/navs,
 * then bolt on the favicon and the AOS visibility failsafe. */
function postprocessPage(html: string, orderHref: string, logoDataUrl: string | null): string {
  let out = fixCtas(html, orderHref);
  out = fixDuplicateImages(out);
  out = stripBreadcrumbs(out);
  if (logoDataUrl) out = injectFavicon(out, logoDataUrl);
  out = injectAosFailsafe(out);
  return out;
}

async function buildAllPages(
  form: OnboardingFormData,
  design: DesignPrefs,
  brief: string,
  chosenMockupHtml: string,
  plan: SitePlan,
  uploadedImages: ExtractedImage[]
): Promise<{ pages: BuiltPage[]; warnings: string[] }> {
  const warnings: string[] = [];
  const siteMap = buildPageSummary(plan.pages);
  const orderPage = findOrderPage(plan.pages);
  const orderHref = `${orderPage.slug}.html`;
  const ctaRule =
    `Every primary call-to-action button (e.g. "${design.cta || "Contact us"}", "Order", "Book", "Contact") ` +
    `MUST be a working link to "${orderHref}" (use <a href="${orderHref}">). Never leave a CTA as href="#" or a dead button.`;

  // One registry for the whole build: every base64 src that could end up in
  // a prompt below — page image catalogs, and chosenMockupHtml, which
  // arrives from the client with a base64 hero photo already baked into its
  // <img> tag from the mockup step — gets swapped for a short token before
  // it's embedded, and swapped back on each page's generated HTML right
  // after it comes back. The model never sees or pays for the actual bytes.
  const registry = createImageRegistry();
  const imageCatalogByPage = await buildImageCatalogs(form, design, plan, uploadedImages, registry);
  const compressedMockupHtml = registry.compress(chosenMockupHtml);
  const logoDataUrl = findLogoDataUrl(uploadedImages);
  // Full pages must clear a higher completeness bar than mockups: a real
  // multi-section page under ~2500 chars is an empty shell, not a page.
  const PAGE_MIN_CHARS = 2500;

  // homepage first (sequential) — inner pages reuse its exact nav/footer markup
  const homePage = plan.pages.find((p) => p.isHome) ?? plan.pages[0];
  const homePrompt = buildPagePrompt({
    page: homePage,
    isHome: true,
    brief,
    chosenMockupHtml: compressedMockupHtml,
    siteMap,
    imageCatalog: imageCatalogByPage[homePage.name] ?? "",
    ctaRule,
    navHtml: "",
    footerHtml: "",
    forbiddenSections: buildForbiddenSections(plan.pages, homePage.name),
    isOrderPage: homePage.slug === orderPage.slug,
    theme: design.theme || "Light mode",
  });
  let homeHtml = await generateHtmlPage(homePrompt, { minChars: PAGE_MIN_CHARS });
  homeHtml = registry.resolve(homeHtml);
  homeHtml = postprocessPage(homeHtml, orderHref, logoDataUrl);
  // Shell extraction happens AFTER cleanup so inner pages inherit the
  // stripped, single-nav version rather than re-propagating a stray
  // breadcrumb bar to every page. homeHtml is already resolved (real image
  // data) at this point, so nav/footer are re-compressed here too, in case
  // the model placed a real image (e.g. a logo) inside either one — same
  // rule either way: nothing with a real `data:` URI enters a prompt below.
  const { nav, footer } = extractShell(homeHtml);
  const compressedNav = registry.compress(nav);
  const compressedFooter = registry.compress(footer);

  const others = plan.pages.filter((p) => p.slug !== homePage.slug);
  // Local 2-at-a-time cap on top of the global OpenRouter queue. The queue
  // is the hard limit on requests in flight; this cap additionally keeps a
  // 5-page plan from parking 5 sets of 16k-token prompts in the queue at
  // once, so a mid-build failure surfaces (and can abort) earlier.
  const CONCURRENCY = 2;
  const builtOthers = await mapWithConcurrency(others, CONCURRENCY, async (pg): Promise<BuiltPage | null> => {
    try {
      const prompt = buildPagePrompt({
        page: pg,
        isHome: false,
        brief,
        chosenMockupHtml: compressedMockupHtml,
        siteMap,
        imageCatalog: imageCatalogByPage[pg.name] ?? "",
        ctaRule,
        navHtml: compressedNav,
        footerHtml: compressedFooter,
        forbiddenSections: buildForbiddenSections(plan.pages, pg.name),
        isOrderPage: pg.slug === orderPage.slug,
        theme: design.theme || "Light mode",
      });
      let html = await generateHtmlPage(prompt, { minChars: PAGE_MIN_CHARS });
      html = registry.resolve(html);
      html = postprocessPage(html, orderHref, logoDataUrl);
      return { name: pg.name, slug: pg.slug, filename: `${pg.slug}.html`, html };
    } catch (err) {
      warnings.push(`Couldn't build the "${pg.name}" page: ${err instanceof Error ? err.message : String(err)}`);
      return null;
    }
  });

  const pages: BuiltPage[] = [
    { name: homePage.name, slug: "index", filename: "index.html", html: homeHtml },
    ...builtOthers.filter((p): p is BuiltPage => p !== null),
  ];

  return { pages, warnings };
}

async function buildViaV0Only(
  form: OnboardingFormData,
  design: DesignPrefs,
  brief: string,
  chosenMockupHtml: string,
  plan: SitePlan,
  uploadedImages: ExtractedImage[]
): Promise<{ v0: V0Result; warnings: string[] }> {
  const imageCatalogByPage = await buildImageCatalogs(form, design, plan, uploadedImages);
  const prompt = buildV0MultiPageBrief(brief, chosenMockupHtml, plan.pages, imageCatalogByPage);
  const v0 = await generateWithV0(prompt);
  return { v0, warnings: [] };
}

/** The single entry point the build API route calls — branches by provider,
 * but every mode shares the same brief and the same approved plan. */
export async function runBuild(
  form: OnboardingFormData,
  design: DesignPrefs,
  provider: GenerationProvider,
  chosenMockupHtml: string,
  plan: SitePlan,
  uploadedImages: ExtractedImage[]
): Promise<PipelineResult> {
  const brief = await prepareBrief(form, design);
  const warnings: string[] = [];

  if (provider === "v0") {
    if (!isV0Configured()) {
      throw new Error("V0_API_KEY isn't configured — add it to .env.local to use v0-based generation, or pick Claude instead.");
    }
    const { v0, warnings: w } = await buildViaV0Only(form, design, brief, chosenMockupHtml, plan, uploadedImages);
    return { provider, pages: [], siteCopy: null, v0, warnings: w };
  }

  const { pages, warnings: buildWarnings } = await buildAllPages(form, design, brief, chosenMockupHtml, plan, uploadedImages);
  warnings.push(...buildWarnings);

  const siteCopy = pages.length > 0 ? await extractSiteCopy(pages[0].html) : null;

  let v0: V0Result | null = null;
  if (provider === "both") {
    if (!isV0Configured()) {
      warnings.push("V0_API_KEY isn't configured, so the site was built with Claude only — v0 hosting was skipped.");
    } else {
      try {
        v0 = await hostMultiPageWithV0(
          pages.map((p) => ({ slug: p.slug, html: p.html })),
          form.companyName
        );
      } catch (err) {
        warnings.push(err instanceof Error ? err.message : String(err));
      }
    }
  }

  return { provider, pages, siteCopy, v0, warnings };
}
