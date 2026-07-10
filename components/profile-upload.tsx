"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProfileExtractionResult } from "@/types/generation";

interface ProfileUploadProps {
  onExtracted: (result: ProfileExtractionResult) => void;
}

export function ProfileUpload({ onExtracted }: ProfileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProfileExtractionResult | null>(null);

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/profile", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Failed to read the file.");
      setResult(data as ProfileExtractionResult);
      onExtracted(data as ProfileExtractionResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to read the file.");
    } finally {
      setLoading(false);
    }
  }

  const fieldCount = result ? Object.values(result.fields).filter((v) => v && v.trim()).length : 0;

  return (
    <Card className="border-dashed p-5">
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium">Have a company profile or portfolio doc?</p>
          <p className="text-xs text-muted-foreground">
            Upload a PDF, DOCX, TXT, or MD and we&rsquo;ll prefill the form below — you can still edit
            anything before continuing. DOCX files also let us pull in your real photos.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={loading}
          onClick={() => inputRef.current?.click()}
        >
          {loading ? "Reading…" : "Upload profile"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {error ? <p className="mt-3 text-xs text-destructive">{error}</p> : null}

      {result ? (
        <div className="mt-4 space-y-2 border-t pt-3">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="success">{result.sourceFilename}</Badge>
            <span className="text-muted-foreground">
              Prefilled {fieldCount} field{fieldCount === 1 ? "" : "s"}
              {result.images.length > 0
                ? `, found ${result.images.length} photo${result.images.length === 1 ? "" : "s"}`
                : ""}
            </span>
          </div>
          {result.images.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {result.images.map((img, i) => (
                // eslint-disable-next-line @next/next/no-img-element -- base64 data URI thumbnails, nothing to optimize
                <img
                  key={i}
                  src={img.dataUrl}
                  alt={img.label}
                  title={img.label}
                  className="h-14 w-14 rounded-md border object-cover"
                />
              ))}
            </div>
          ) : null}
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-500">
              {w}
            </p>
          ))}
        </div>
      ) : null}
    </Card>
  );
}
