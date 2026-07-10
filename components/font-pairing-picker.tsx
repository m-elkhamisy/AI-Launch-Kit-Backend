"use client";

import { useState, type ReactNode } from "react";
import { Check, Sparkles, Type as TypeIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useGoogleFonts } from "@/lib/use-google-fonts";
import { AI_CHOICE_ID, CUSTOM_ID, FONT_PAIRINGS, FontChoice } from "@/types/design";
import { CustomFontModal } from "@/components/custom-font-modal";

interface FontPairingPickerProps {
  fontPairingId: string;
  customFonts: FontChoice | null;
  onSelect: (id: string) => void;
  onCustomFontsChange: (fonts: FontChoice) => void;
}

export function FontPairingPicker({
  fontPairingId,
  customFonts,
  onSelect,
  onCustomFontsChange,
}: FontPairingPickerProps) {
  const [modalOpen, setModalOpen] = useState(false);

  const previewHeadings = FONT_PAIRINGS.map((f) => f.heading);
  if (fontPairingId === CUSTOM_ID && customFonts?.heading) previewHeadings.push(customFonts.heading);
  useGoogleFonts(previewHeadings);

  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Font pairings</h3>
      <p className="mb-3 text-xs text-muted-foreground">Every page will use this heading + body combination.</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {FONT_PAIRINGS.map((opt) => (
          <FontTile
            key={opt.id}
            category={opt.category}
            heading={opt.heading}
            body={opt.body}
            selected={fontPairingId === opt.id}
            onClick={() => onSelect(opt.id)}
          />
        ))}
        <FontTile
          category="AI choice"
          heading={null}
          body={null}
          icon={<Sparkles className="h-4 w-4" />}
          caption="Let the AI pick a pairing that fits the brand"
          selected={fontPairingId === AI_CHOICE_ID}
          onClick={() => onSelect(AI_CHOICE_ID)}
        />
        <FontTile
          category="Custom"
          heading={fontPairingId === CUSTOM_ID ? customFonts?.heading ?? null : null}
          body={fontPairingId === CUSTOM_ID ? customFonts?.body ?? null : null}
          icon={<TypeIcon className="h-4 w-4" />}
          caption={fontPairingId === CUSTOM_ID ? undefined : "Choose fonts"}
          selected={fontPairingId === CUSTOM_ID}
          onClick={() => setModalOpen(true)}
        />
      </div>

      <CustomFontModal
        open={modalOpen}
        initialValue={customFonts ?? { heading: "Poppins", body: "Inter" }}
        onCancel={() => setModalOpen(false)}
        onApply={(fonts) => {
          onCustomFontsChange(fonts);
          setModalOpen(false);
        }}
      />
    </div>
  );
}

function FontTile({
  category,
  heading,
  body,
  icon,
  caption,
  selected,
  onClick,
}: {
  category: string;
  heading: string | null;
  body: string | null;
  icon?: ReactNode;
  caption?: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-xl border p-4 text-left transition-colors",
        selected ? "border-primary bg-primary/5 ring-1 ring-primary/30" : "border-border hover:border-muted-foreground/40"
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{category}</span>
        {selected ? <Check className="h-3.5 w-3.5 shrink-0 text-primary" /> : null}
      </div>
      {heading ? (
        <>
          <p className="truncate text-xl font-semibold leading-tight" style={{ fontFamily: `"${heading}", sans-serif` }}>
            {heading}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{body} — body text</p>
        </>
      ) : (
        <div className="flex items-center gap-2 py-1.5 text-sm text-muted-foreground">
          {icon}
          {caption}
        </div>
      )}
    </button>
  );
}
