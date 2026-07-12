import {
  AI_CHOICE_ID,
  COLOR_PALETTES,
  CUSTOM_ID,
  ColorSwatch,
  DesignPrefs,
  FONT_PAIRINGS,
  FontChoice,
} from "@/types/design";

/** Resolves the chosen palette's actual hex values, or null when the AI is
 * left to choose one at build time. */
export function resolvePaletteColors(design: DesignPrefs): ColorSwatch | null {
  if (design.paletteId === CUSTOM_ID) return design.customPalette;
  if (design.paletteId === AI_CHOICE_ID) return null;
  return COLOR_PALETTES.find((p) => p.id === design.paletteId)?.colors ?? null;
}

/** Resolves the chosen heading/body font names, or null when the AI is left
 * to choose one at build time. */
export function resolveFontChoice(design: DesignPrefs): FontChoice | null {
  if (design.fontPairingId === CUSTOM_ID) return design.customFonts;
  if (design.fontPairingId === AI_CHOICE_ID) return null;
  const preset = FONT_PAIRINGS.find((f) => f.id === design.fontPairingId);
  return preset ? { heading: preset.heading, body: preset.body } : null;
}

/** Human-readable "color mood" line — fills the same DESIGN PREFERENCES slot
 * in the prompt brief (and the PDF brief) that the old free-text pill used
 * to fill directly from `design.palette`. */
export function describePalette(design: DesignPrefs): string {
  const colors = resolvePaletteColors(design);
  if (!colors) return "Let the AI choose to fit the brand";
  const name =
    design.paletteId === CUSTOM_ID
      ? "Custom palette"
      : COLOR_PALETTES.find((p) => p.id === design.paletteId)?.name ?? "Custom palette";
  return `${name} (primary ${colors.primary}, secondary ${colors.secondary}, background ${colors.background}, text ${colors.text})`;
}

/** Human-readable "typography feel" line — same slot `design.fonts` used to
 * fill directly. */
export function describeFonts(design: DesignPrefs): string {
  const fonts = resolveFontChoice(design);
  if (!fonts) return "Let the AI choose";
  const name =
    design.fontPairingId === CUSTOM_ID
      ? "Custom pairing"
      : FONT_PAIRINGS.find((f) => f.id === design.fontPairingId)?.category ?? "Custom pairing";
  return `${name} — ${fonts.heading} (headings) + ${fonts.body} (body)`;
}

/**
 * Precise design-token block appended to the AI brief when the client picked
 * exact colors/fonts, so generation matches them exactly instead of only
 * approximating a mood description. Returns "" when both are left to the AI
 * (nothing concrete to pin down), so the brief doesn't grow for no reason.
 */
export function buildDesignTokensBlock(design: DesignPrefs): string {
  const colors = resolvePaletteColors(design);
  const fonts = resolveFontChoice(design);
  if (!colors && !fonts) return "";

  const lines: string[] = ["EXACT DESIGN TOKENS — use these precisely, do not substitute different values:"];
  if (colors) {
    lines.push(
      `- Primary color: ${colors.primary}`,
      `- Secondary color: ${colors.secondary}`,
      `- Background color: ${colors.background}`,
      `- Text color: ${colors.text}`
    );
  }
  if (fonts) {
    lines.push(
      `- Heading font: "${fonts.heading}" (load from Google Fonts)`,
      `- Body font: "${fonts.body}" (load from Google Fonts)`
    );
  }
  return lines.join("\n");
}
