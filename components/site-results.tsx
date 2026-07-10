"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useDownloads } from "@/hooks/use-downloads";
import { OnboardingFormData } from "@/types/form";
import { DesignPrefs } from "@/types/design";
import { PipelineResult } from "@/types/generation";

interface SiteResultsProps {
  result: PipelineResult;
  form: OnboardingFormData;
  design: DesignPrefs;
  onStartOver: () => void;
}

export function SiteResults({ result, form, design, onStartOver }: SiteResultsProps) {
  const { downloading, downloadPdf, downloadHtml, downloadZip } = useDownloads();
  const pages = result.pages ?? [];
  const [activeSlug, setActiveSlug] = useState(pages[0]?.slug ?? "");

  const activePage = pages.find((p) => p.slug === activeSlug) ?? pages[0];

  return (
    <div className="space-y-5">
      {result.warnings.length > 0 ? (
        <Card className="border-amber-500/40 bg-amber-500/5 p-4">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-500">
              {w}
            </p>
          ))}
        </Card>
      ) : null}

      {result.v0 ? (
        <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <p className="text-sm font-medium">Live on v0</p>
            <p className="text-xs text-muted-foreground">
              {result.v0.status === "completed" ? "Build complete." : "Still finishing up — refresh the link in a moment if it looks incomplete."}
            </p>
          </div>
          <div className="flex gap-2">
            {result.v0.demoUrl ? (
              <Button size="sm" asChild>
                <a href={result.v0.demoUrl} target="_blank" rel="noreferrer">
                  Open live preview
                </a>
              </Button>
            ) : null}
            <Button size="sm" variant="outline" asChild>
              <a href={result.v0.webUrl} target="_blank" rel="noreferrer">
                Open in v0
              </a>
            </Button>
          </div>
        </Card>
      ) : null}

      {pages.length > 0 ? (
        <>
          <div className="flex flex-wrap gap-2">
            {pages.map((p) => (
              <button
                key={p.slug}
                onClick={() => setActiveSlug(p.slug)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-xs transition-colors",
                  activeSlug === p.slug
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input hover:bg-accent"
                )}
              >
                {p.name}
              </button>
            ))}
          </div>

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b bg-muted/40 px-3 py-2">
              <span className="text-xs text-muted-foreground">{activePage?.filename}</span>
              <Button
                size="sm"
                variant="ghost"
                disabled={!activePage || downloading === "html"}
                onClick={() => activePage && downloadHtml(activePage.html, form.companyName)}
              >
                Download this page
              </Button>
            </div>
            {activePage ? (
              <iframe srcDoc={activePage.html} className="h-[70vh] w-full border-0" title={activePage.name} />
            ) : null}
          </Card>
        </>
      ) : null}

      {result.siteCopy ? (
        <Card className="p-4">
          <p className="mb-2 text-sm font-medium">Copy summary</p>
          <p className="text-sm font-semibold">{result.siteCopy.headline}</p>
          <p className="mb-2 text-xs text-muted-foreground">{result.siteCopy.subheadline}</p>
          <Badge variant="outline">{result.siteCopy.callToAction}</Badge>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-3 border-t pt-4">
        {pages.length > 0 ? (
          <Button
            variant="outline"
            disabled={downloading === "zip"}
            onClick={() => downloadZip(pages, form.companyName)}
          >
            {downloading === "zip" ? "Zipping…" : "Download all pages (.zip)"}
          </Button>
        ) : null}
        <Button variant="outline" disabled={downloading === "pdf"} onClick={() => downloadPdf(form, design)}>
          {downloading === "pdf" ? "Preparing…" : "Download brief (.pdf)"}
        </Button>
        <Button variant="ghost" onClick={onStartOver}>
          Start a new site
        </Button>
      </div>
    </div>
  );
}
