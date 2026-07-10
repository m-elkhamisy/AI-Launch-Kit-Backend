import { PlannedPage } from "@/types/generation";

export function renderPlanText(pages: PlannedPage[]): string {
  return pages
    .map((pg, i) => {
      const lines = [`${i + 1}. ${pg.name}${pg.purpose ? `  —  ${pg.purpose}` : ""}`];
      if (pg.sections.length) lines.push("     sections: " + pg.sections.join(" · "));
      return lines.join("\n");
    })
    .join("\n\n");
}
