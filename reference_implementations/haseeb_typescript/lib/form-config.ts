import { FormFieldConfig, OnboardingFormData } from "@/types/form";

export const SECTION_ORDER: FormFieldConfig["section"][] = [
  "identity",
  "audience",
  "proof",
  "practical",
  "voice",
  "extra",
];

export const SECTION_LABELS: Record<
  FormFieldConfig["section"],
  { title: string; helpText?: string }
> = {
  identity: { title: "1. Identity" },
  audience: { title: "2. Audience & positioning" },
  proof: {
    title: "3. Proof & facts",
    helpText:
      "Leave any of these blank if you don't have them yet — we will NOT invent stats, testimonials, or team bios to fill the gap. Real answers here make the biggest difference to how believable the site feels.",
  },
  practical: { title: "4. Practical details" },
  voice: { title: "5. Voice & aesthetic notes" },
  extra: { title: "6. Anything else" },
};

export const FORM_FIELDS: FormFieldConfig[] = [
  // ---- identity ----
  {
    key: "companyName",
    label: "Company / brand name",
    placeholder: "e.g. Cedar & Stone Bakery",
    type: "input",
    required: true,
    section: "identity",
  },
  {
    key: "industry",
    label: "Industry",
    placeholder: "e.g. Artisan bakery and café",
    type: "input",
    required: true,
    section: "identity",
  },
  {
    key: "activityCode",
    label: "Trade licence / activity code",
    placeholder: "e.g. 4711 — if you have one",
    type: "input",
    section: "identity",
    helpText: "Optional — only relevant if you're formally registered under a specific activity code.",
  },
  {
    key: "businessActivity",
    label: "What does the business actually do, day to day?",
    placeholder:
      "e.g. We bake and sell sourdough bread, pastries, and custom celebration cakes from a single storefront, plus wholesale to 6 local cafés.",
    type: "textarea",
    required: true,
    section: "identity",
  },

  // ---- audience ----
  {
    key: "targetAudience",
    label: "Who is this website for?",
    placeholder:
      "e.g. Local families and young professionals within a 15-minute drive, plus cafés looking for a wholesale bread supplier",
    type: "textarea",
    required: true,
    section: "audience",
  },
  {
    key: "uvp",
    label: "What makes you different from the alternative down the street?",
    placeholder:
      "e.g. Everything is made from a 12-year-old sourdough starter, flour sourced from two named local farms, nothing frozen",
    type: "textarea",
    required: true,
    section: "audience",
  },
  {
    key: "competitors",
    label: "Who are you up against?",
    placeholder: "e.g. Two chain bakeries nearby — we want to feel more handmade and personal than they do",
    type: "textarea",
    section: "audience",
    helpText: "Used only to shape tone/positioning — we never name competitors in the copy.",
  },
  {
    key: "purpose",
    label: "What's the #1 job this website needs to do?",
    placeholder: "e.g. Get people to place online orders for pickup, and get wholesale cafés to enquire",
    type: "textarea",
    section: "audience",
  },

  // ---- proof ----
  {
    key: "stats",
    label: "Any real numbers worth featuring?",
    placeholder: "e.g. Founded 2014, 3 locations, 40,000 loaves baked last year",
    type: "textarea",
    section: "proof",
    helpText: "Only real figures — leave blank rather than let us guess.",
  },
  {
    key: "testimonials",
    label: "Got a real customer quote or two?",
    placeholder: "Paste 1-3 short real quotes, with the customer's first name if you have permission to use it",
    type: "textarea",
    section: "proof",
  },
  {
    key: "teamBios",
    label: "Team or founders to feature",
    placeholder: "e.g. Amir Hassan, Head Baker — trained in Lyon, runs the ovens every morning",
    type: "textarea",
    section: "proof",
  },
  {
    key: "certifications",
    label: "Certifications, awards, or press",
    placeholder: "e.g. Halal certified, \u201cBest New Bakery 2023\u201d \u2014 Time Out",
    type: "textarea",
    section: "proof",
  },

  // ---- practical ----
  {
    key: "products",
    label: "Main products or services to list",
    placeholder: "e.g. Sourdough loaves, croissants, custom cakes (with lead time), wholesale bread accounts",
    type: "textarea",
    section: "practical",
  },
  {
    key: "locationHours",
    label: "Address and opening hours",
    placeholder: "e.g. 12 Marina Walk, Dubai — Mon\u2013Sat 7am\u20137pm, closed Sundays",
    type: "textarea",
    section: "practical",
    helpText:
      "We will never invent an address, phone number, or hours — leave this blank and the site uses a generic \u201ccontact us\u201d prompt instead.",
  },
  {
    key: "serviceArea",
    label: "Area you serve (if relevant)",
    placeholder: "e.g. Delivery within Dubai Marina and JBR only",
    type: "input",
    section: "practical",
  },
  {
    key: "contact",
    label: "Preferred contact details",
    placeholder: "e.g. hello@cedarstone.ae, +971 4 123 4567",
    type: "input",
    section: "practical",
  },
  {
    key: "socials",
    label: "Social links",
    placeholder: "e.g. instagram.com/cedarstonebakery",
    type: "input",
    section: "practical",
  },

  // ---- voice ----
  {
    key: "tone",
    label: "How should the writing sound?",
    placeholder: "e.g. Warm and a little playful, never corporate",
    type: "input",
    section: "voice",
  },
  {
    key: "aesthetic",
    label: "Any visual references or must-avoids?",
    placeholder: "e.g. Love the feel of a Parisian patisserie; please no stock photos of random bread",
    type: "textarea",
    section: "voice",
  },

  // ---- extra ----
  {
    key: "description",
    label: "One paragraph, in your own words",
    placeholder: "Describe the business like you're telling a friend about it",
    type: "textarea",
    section: "extra",
  },
  {
    key: "notes",
    label: "Anything else the site absolutely must include or avoid?",
    placeholder: "e.g. Must mention we're closed for Eid week, avoid red (used by a competitor)",
    type: "textarea",
    section: "extra",
  },
];

export const EMPTY_FORM_DATA: OnboardingFormData = FORM_FIELDS.reduce((acc, f) => {
  acc[f.key] = "";
  return acc;
}, {} as OnboardingFormData);

export function fieldsForSection(section: FormFieldConfig["section"]): FormFieldConfig[] {
  return FORM_FIELDS.filter((f) => f.section === section);
}
