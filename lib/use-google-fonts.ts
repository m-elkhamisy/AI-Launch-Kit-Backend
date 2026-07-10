"use client";

import { useEffect } from "react";

/** Module-level so the same family is never requested twice across the
 * whole app, no matter how many pickers/previews ask for it. */
const loadedFamilies = new Set<string>();

/**
 * Injects a Google Fonts stylesheet <link> for the given family names, so a
 * font-pairing tile or preview can render real text in that font instead of
 * just naming it. Browser-only and idempotent — safe to call from any
 * client component, including several at once.
 */
export function useGoogleFonts(families: string[]) {
  const key = families.filter(Boolean).join("|");

  useEffect(() => {
    if (!key) return;
    const toLoad = key.split("|").filter((f) => !loadedFamilies.has(f));
    if (toLoad.length === 0) return;
    toLoad.forEach((f) => loadedFamilies.add(f));

    const query = toLoad
      .map((f) => `family=${encodeURIComponent(f).replace(/%20/g, "+")}:wght@400;500;600;700`)
      .join("&");
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `https://fonts.googleapis.com/css2?${query}&display=swap`;
    link.dataset.dynamicGoogleFont = "true";
    document.head.appendChild(link);
  }, [key]);
}
