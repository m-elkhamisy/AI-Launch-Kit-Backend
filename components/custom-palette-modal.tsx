"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { ColorSwatch } from "@/types/design";

const FIELDS: { key: keyof ColorSwatch; label: string }[] = [
  { key: "primary", label: "Primary" },
  { key: "secondary", label: "Secondary" },
  { key: "background", label: "Background" },
  { key: "text", label: "Text" },
];

const HEX_RE = /^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$/;

interface CustomPaletteModalProps {
  open: boolean;
  initialValue: ColorSwatch;
  onCancel: () => void;
  onApply: (swatch: ColorSwatch) => void;
}

export function CustomPaletteModal({ open, initialValue, onCancel, onApply }: CustomPaletteModalProps) {
  const [draft, setDraft] = useState<ColorSwatch>(initialValue);
  const [showPreview, setShowPreview] = useState(false);
  const [wasOpen, setWasOpen] = useState(open);

  // Re-sync the draft to whatever was last applied every time the modal
  // transitions to open, so a Cancel never leaks into the next open.
  // Adjusted during render — React's documented pattern for resetting state
  // on a prop change — rather than in an effect, which would cost an extra
  // render pass after the one that actually shows the modal.
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setDraft(initialValue);
  }

  function setField(key: keyof ColorSwatch, v: string) {
    setDraft((prev) => ({ ...prev, [key]: v }));
  }

  const allValid = FIELDS.every((f) => HEX_RE.test(draft[f.key]));

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Custom Palette</DialogTitle>
          <Button type="button" variant="ghost" size="sm" onClick={() => setShowPreview((s) => !s)}>
            {showPreview ? "Hide" : "Preview"}
          </Button>
        </DialogHeader>

        <div className="space-y-4">
          {FIELDS.map((f) => {
            const valid = HEX_RE.test(draft[f.key]);
            return (
              <div key={f.key} className="flex items-center gap-3">
                <input
                  type="color"
                  value={valid ? draft[f.key] : "#000000"}
                  onChange={(e) => setField(f.key, e.target.value)}
                  aria-label={`${f.label} color`}
                  className="h-10 w-10 shrink-0 cursor-pointer rounded-md border border-input bg-transparent p-0.5"
                />
                <div className="flex-1">
                  <Label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">{f.label}</Label>
                  <input
                    value={draft[f.key]}
                    onChange={(e) => setField(f.key, e.target.value)}
                    placeholder="#000000"
                    spellCheck={false}
                    className={cn(
                      "flex h-10 w-full rounded-md border bg-card px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      valid ? "border-input" : "border-destructive text-destructive"
                    )}
                  />
                </div>
              </div>
            );
          })}

          {showPreview ? (
            <div
              className="rounded-lg border p-4 transition-colors"
              style={{ background: draft.background, color: draft.text, borderColor: draft.secondary }}
            >
              <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: draft.secondary }}>
                Preview
              </p>
              <p className="mt-1 text-lg font-semibold">Your headline goes here</p>
              <p className="mt-1 text-sm opacity-80">Body copy sample using the text and background colors above.</p>
              <span
                className="mt-3 inline-block rounded-md px-3 py-1.5 text-sm font-medium"
                style={{ background: draft.primary, color: draft.background }}
              >
                Call to action
              </span>
            </div>
          ) : null}
        </div>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" disabled={!allValid} onClick={() => onApply(draft)}>
            Apply
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
