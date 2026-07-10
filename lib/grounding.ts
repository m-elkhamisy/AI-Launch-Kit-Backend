import { OnboardingFormData } from "@/types/form";

/**
 * The single biggest source of hallucinated sites in the old prompts was
 * an instruction like "write real, specific copy, no lorem ipsum" with
 * nothing telling the model what to do when it doesn't actually have a
 * specific. Left there, it invents one — a founding year, a client count,
 * a named testimonial — because a specific-sounding number reads as more
 * "real" than an honest generic sentence.
 *
 * Fix has two parts, both applied together everywhere copy is generated:
 *  1. FACT_DISCIPLINE — explicit rules for what to do with a gap.
 *  2. renderFactSheet() — turns the brief into a sheet that separates
 *     "stated facts" from "not provided, do not invent" per category,
 *     so the model isn't left guessing which parts are verified.
 */
export const FACT_DISCIPLINE = `
FACTUAL DISCIPLINE — this overrides any instinct to make the copy sound more impressive:
- Only state facts that appear in the FACT SHEET below. Never invent: founding
  years, years-in-business, client/customer counts, project counts, revenue,
  team size, award names, certifications, press mentions, or named
  testimonials/reviewers that are not explicitly given.
- Sections marked "NOT PROVIDED" in the fact sheet must not be papered over
  with invented specifics. Instead, for that section:
    (a) omit the specific claim or the section entirely, OR
    (b) write it without a fabricated number/name (e.g. "trusted by clients
        across the region" instead of "trusted by 500+ clients"), OR
    (c) leave a clearly marked placeholder comment, e.g.
        <!-- ADD: a real client testimonial here --> in HTML, or an obvious
        bracketed placeholder in JSX, so a human can fill it in later.
  Never fabricate a plausible-sounding number, date, name, or quote to fill a
  gap — an honest generic sentence is always correct over an invented specific.
- If the fact sheet DOES include real stats, testimonials, certifications, or
  team bios, use them as given — light copy-editing for flow is fine, but
  don't alter a number, a name, or the substance of a quote.
- Contact details (address, phone, email, hours) come only from the fact
  sheet. If a detail isn't listed, use a generic call to action ("Contact us
  for hours") or an obviously-marked placeholder — never invent an address,
  phone number, or opening hours.
- Never name real competing companies or real people who aren't in the fact
  sheet, and never make legal, medical, or financial claims the fact sheet
  doesn't support.
`.trim();

interface FactField {
  label: string;
  value: string;
}

function factBlock(title: string, fields: FactField[], emptyNote: string): string {
  const given = fields.filter((f) => f.value.trim());
  if (given.length === 0) {
    return `${title}: NOT PROVIDED — ${emptyNote}`;
  }
  return (
    `${title} (verified, use as-is):\n` +
    given.map((f) => `  - ${f.label}: ${f.value.trim()}`).join("\n")
  );
}

/** Renders the brief into fact-checked sections. This is what every prompt
 * builder should quote from instead of re-serializing the raw form. */
export function renderFactSheet(form: OnboardingFormData): string {
  const sections = [
    factBlock(
      "IDENTITY",
      [
        { label: "Company", value: form.companyName },
        { label: "Industry", value: form.industry },
        { label: "Activity classification", value: form.activityCode },
        { label: "What the business does", value: form.businessActivity },
      ],
      "do not invent an industry or business description."
    ),
    factBlock(
      "AUDIENCE & POSITIONING",
      [
        { label: "Target audience", value: form.targetAudience },
        { label: "Unique value proposition", value: form.uvp },
        { label: "Competitors to differentiate from", value: form.competitors },
        { label: "Purpose of this site", value: form.purpose },
      ],
      "keep positioning language generic rather than inventing a differentiator."
    ),
    factBlock(
      "PROOF & STATS",
      [
        { label: "Stats / achievements", value: form.stats },
        { label: "Testimonials (real quotes)", value: form.testimonials },
        { label: "Team / founders", value: form.teamBios },
        { label: "Certifications / awards", value: form.certifications },
      ],
      "do NOT invent stats, testimonials, team members, or awards. Omit these claims or use the placeholder approach described in FACTUAL DISCIPLINE."
    ),
    factBlock(
      "PRACTICAL DETAILS",
      [
        { label: "Products / services", value: form.products },
        { label: "Location & hours", value: form.locationHours },
        { label: "Service area", value: form.serviceArea },
        { label: "Contact details", value: form.contact },
        { label: "Social links", value: form.socials },
      ],
      "do NOT invent an address, phone number, hours, or service area."
    ),
    factBlock(
      "VOICE",
      [
        { label: "Tone", value: form.tone },
        { label: "Aesthetic notes", value: form.aesthetic },
      ],
      "choose a tone that fits the industry and audience above."
    ),
    factBlock(
      "ADDITIONAL CONTEXT",
      [
        { label: "Description", value: form.description },
        { label: "Notes / must-haves", value: form.notes },
      ],
      "none given."
    ),
  ];
  return sections.join("\n\n");
}
