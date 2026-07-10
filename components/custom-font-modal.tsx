"use client";

import { useEffect, useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useGoogleFonts } from "@/lib/use-google-fonts";
import { FontChoice, GOOGLE_FONT_CHOICES } from "@/types/design";

interface CustomFontModalProps {
  open: boolean;
  initialValue: FontChoice;
  onCancel: () => void;
  onApply: (fonts: FontChoice) => void;
}

export function CustomFontModal({ open, initialValue, onCancel, onApply }: CustomFontModalProps) {
  const [draft, setDraft] = useState<FontChoice>(initialValue);
  const [showPreview, setShowPreview] = useState(false);
  const [wasOpen, setWasOpen] = useState(open);

  // Re-sync the draft every time the modal transitions to open, so a Cancel
  // never leaks into the next open. Adjusted during render rather than in
  // an effect — see the identical comment in custom-palette-modal.tsx.
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setDraft(initialValue);
  }

  useGoogleFonts(open ? [draft.heading, draft.body] : []);

  const bothChosen = draft.heading.trim().length > 0 && draft.body.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Custom Font Pairing</DialogTitle>
          <Button type="button" variant="ghost" size="sm" onClick={() => setShowPreview((s) => !s)}>
            {showPreview ? "Hide" : "Preview"}
          </Button>
        </DialogHeader>

        <div className="space-y-5">
          <FontSearchField
            label="Heading font"
            value={draft.heading}
            onChange={(v) => setDraft((d) => ({ ...d, heading: v }))}
          />
          <FontSearchField
            label="Body font"
            value={draft.body}
            onChange={(v) => setDraft((d) => ({ ...d, body: v }))}
          />

          {showPreview ? (
            <div className="rounded-lg border p-4">
              <p style={{ fontFamily: `"${draft.heading}", sans-serif` }} className="text-2xl font-semibold">
                {draft.heading || "Heading"}
              </p>
              <p style={{ fontFamily: `"${draft.body}", sans-serif` }} className="mt-1.5 text-sm text-muted-foreground">
                {draft.body || "Body"} — The quick brown fox jumps over the lazy dog.
              </p>
            </div>
          ) : null}
        </div>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" disabled={!bothChosen} onClick={() => onApply(draft)}>
            Apply
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function FontSearchField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [prevValue, setPrevValue] = useState(value);

  if (value !== prevValue) {
    setPrevValue(value);
    setQuery(value);
  }

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  const matches = GOOGLE_FONT_CHOICES.filter((f) => f.toLowerCase().includes(query.toLowerCase())).slice(0, 8);

  return (
    <div ref={containerRef} className="relative">
      <Label className="mb-1.5 block text-xs uppercase tracking-wide text-muted-foreground">{label}</Label>
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="Search fonts…"
        spellCheck={false}
        className="flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
      {open && matches.length > 0 ? (
        <div className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-md border border-border bg-popover p-1 shadow-md">
          {matches.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => {
                onChange(f);
                setQuery(f);
                setOpen(false);
              }}
              className={cn("block w-full rounded px-2.5 py-1.5 text-left text-sm hover:bg-accent", f === value && "bg-accent")}
            >
              {f}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
