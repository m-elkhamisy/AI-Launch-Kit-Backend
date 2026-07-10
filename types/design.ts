/**
 * Look-and-feel choices, asked once and applied across the whole site
 * regardless of which generation mode builds it. Kept separate from
 * OnboardingFormData because these render as pill/button/swatch pickers
 * rather than free text.
 */

// ---------------------------------------------------------------------------
// Colors & Fonts — structured choices (exact hex values / font names), not
// just a mood word. This lets the "Colors & Fonts" step render real swatches
// and font previews, and lets the AI brief carry precise design tokens (see
// lib/design-utils.ts -> buildDesignTokensBlock) instead of only a vibe.
// ---------------------------------------------------------------------------

export interface ColorSwatch {
  primary: string;
  secondary: string;
  background: string;
  text: string;
}

export interface ColorPaletteOption {
  id: string;
  name: string;
  colors: ColorSwatch;
}

/** Seven curated starting palettes shown as swatch tiles in the "Colors &
 * Fonts" step. Order matches the reference design (theme-mode grid). */
export const COLOR_PALETTES: ColorPaletteOption[] = [
  { id: "modern-blue", name: "Modern Blue", colors: { primary: "#3B6FED", secondary: "#8FB8F7", background: "#F5F8FF", text: "#101B33" } },
  { id: "nature-green", name: "Nature Green", colors: { primary: "#359355", secondary: "#A6E3B4", background: "#F2FBF4", text: "#12301C" } },
  { id: "elegant-purple", name: "Elegant Purple", colors: { primary: "#8B5CF6", secondary: "#D8CCFB", background: "#F8F6FE", text: "#241638" } },
  { id: "warm-orange", name: "Warm Orange", colors: { primary: "#E2803B", secondary: "#F3C89A", background: "#FDF6EC", text: "#4A2A12" } },
  { id: "minimal", name: "Minimal", colors: { primary: "#18181B", secondary: "#8A8A93", background: "#FFFFFF", text: "#18181B" } },
  { id: "luxury-gold", name: "Luxury Gold", colors: { primary: "#C6A15B", secondary: "#E8D08A", background: "#17140F", text: "#FBF6EA" } },
  { id: "soft-pink", name: "Soft Pink", colors: { primary: "#DB5F94", secondary: "#F6C6DD", background: "#FFF6FA", text: "#5B1D3B" } },
];

export const DEFAULT_CUSTOM_PALETTE: ColorSwatch = {
  primary: "#3B6FED",
  secondary: "#8FB8F7",
  background: "#FFFFFF",
  text: "#111111",
};

export interface FontChoice {
  heading: string;
  body: string;
}

export interface FontPairingOption {
  id: string;
  category: string;
  heading: string;
  body: string;
}

/** Eight curated heading/body pairings shown as cards in the "Colors &
 * Fonts" step. All real, freely-available Google Fonts. */
export const FONT_PAIRINGS: FontPairingOption[] = [
  { id: "modern-startup", category: "Modern Startup", heading: "Poppins", body: "Inter" },
  { id: "elegant-editorial", category: "Elegant Editorial", heading: "Playfair Display", body: "Source Sans 3" },
  { id: "corporate", category: "Corporate", heading: "Montserrat", body: "Open Sans" },
  { id: "professional-blog", category: "Professional Blog", heading: "Merriweather", body: "Lato" },
  { id: "tech-saas", category: "Tech & SaaS", heading: "Space Grotesk", body: "Inter" },
  { id: "luxury-brand", category: "Luxury Brand", heading: "DM Serif Display", body: "Manrope" },
  { id: "creative-studio", category: "Creative Studio", heading: "Bebas Neue", body: "Nunito Sans" },
];

export const DEFAULT_CUSTOM_FONTS: FontChoice = {
  heading: "Poppins",
  body: "Inter",
};

/** Curated for the "Custom Font Pairing" search boxes — common, reliable
 * Google Fonts spanning serif/sans/display, not the entire Fonts catalog.
 * Typing a name that isn't in this list still works; these are shortcuts. */
export const GOOGLE_FONT_CHOICES: string[] = [
  "Inter", "Poppins", "Roboto", "Open Sans", "Lato", "Montserrat", "Source Sans 3",
  "Nunito Sans", "Manrope", "Work Sans", "DM Sans", "Karla", "Rubik", "Mulish",
  "Playfair Display", "Merriweather", "DM Serif Display", "Lora", "Cormorant Garamond",
  "Libre Baskerville", "Crimson Pro", "Bitter", "PT Serif",
  "Bebas Neue", "Space Grotesk", "Oswald", "Archivo", "Barlow", "Sora", "Outfit",
  "Fraunces", "Josefin Sans", "Quicksand", "Raleway", "Urbanist", "Plus Jakarta Sans",
  "IBM Plex Sans", "IBM Plex Serif", "Newsreader", "Spectral", "Figtree", "Epilogue",
];

/** Kept out of COLOR_PALETTES/FONT_PAIRINGS so it never collides with a real
 * preset id. Selecting it hands the decision to the model at build time —
 * the same "Let the AI choose" behavior the original text-pill version of
 * this form had, just re-homed as its own tile in the new swatch grid. */
export const AI_CHOICE_ID = "ai-choice";
export const CUSTOM_ID = "custom";

export interface DesignPrefs {
  tagline: string;
  style: string;
  animation: string;
  /** Light mode, dark mode, or both with a working toggle — drives the
   * THEME IMPLEMENTATION block in the page-build prompts. */
  theme: string;
  cta: string;
  imageSource: "pexels" | "ai" | "uploaded" | "placeholder";

  /** One of COLOR_PALETTES[].id, AI_CHOICE_ID, or CUSTOM_ID. */
  paletteId: string;
  /** Populated only when paletteId === CUSTOM_ID. */
  customPalette: ColorSwatch | null;
  /** One of FONT_PAIRINGS[].id, AI_CHOICE_ID, or CUSTOM_ID. */
  fontPairingId: string;
  /** Populated only when fontPairingId === CUSTOM_ID. */
  customFonts: FontChoice | null;
}

export const STYLE_OPTIONS = [
  "Luxury / elegant",
  "Modern / minimal",
  "Bold / playful",
  "Corporate / professional",
  "Warm / organic",
  "Dark / premium tech",
] as const;

export const ANIMATION_OPTIONS = [
  "None (static)",
  "Subtle (gentle fades on scroll)",
  "Medium (hover effects + scroll reveals)",
  "High (rich motion everywhere)",
] as const;

export const THEME_OPTIONS = [
  "Light mode",
  "Dark mode",
  "Light + dark (theme toggle)",
] as const;

export const EMPTY_DESIGN_PREFS: DesignPrefs = {
  tagline: "",
  style: STYLE_OPTIONS[1],
  animation: ANIMATION_OPTIONS[2],
  theme: THEME_OPTIONS[0],
  cta: "",
  imageSource: "placeholder",
  paletteId: AI_CHOICE_ID,
  customPalette: null,
  fontPairingId: AI_CHOICE_ID,
  customFonts: null,
};
