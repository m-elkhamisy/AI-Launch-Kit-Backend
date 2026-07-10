"use client";

import { useState } from "react";
import { OnboardingFormData } from "@/types/form";
import { DesignPrefs } from "@/types/design";
import { BuiltPage } from "@/types/generation";

async function downloadBlob(res: Response, fallbackFilename: string) {
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || "Download failed.");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] || fallbackFilename;

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function useDownloads() {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function downloadPdf(form: OnboardingFormData, design?: DesignPrefs) {
    setDownloading("pdf");
    setError(null);
    try {
      const res = await fetch("/api/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ form, design }),
      });
      await downloadBlob(res, "brief.pdf");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download the PDF.");
    } finally {
      setDownloading(null);
    }
  }

  async function downloadHtml(html: string, companyName: string) {
    setDownloading("html");
    setError(null);
    try {
      const res = await fetch("/api/download-html", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html, companyName }),
      });
      await downloadBlob(res, "site.html");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download the HTML.");
    } finally {
      setDownloading(null);
    }
  }

  async function downloadZip(pages: BuiltPage[], companyName: string) {
    setDownloading("zip");
    setError(null);
    try {
      const res = await fetch("/api/site/zip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pages, companyName }),
      });
      await downloadBlob(res, "site.zip");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download the ZIP.");
    } finally {
      setDownloading(null);
    }
  }

  return { downloading, error, downloadPdf, downloadHtml, downloadZip };
}
