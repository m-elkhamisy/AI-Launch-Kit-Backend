"use client";

import { useState, type ReactNode } from "react";
import { Check, Palette as PaletteIcon, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { AI_CHOICE_ID, COLOR_PALETTES, CUSTOM_ID, ColorSwatch, DEFAULT_CUSTOM_PALETTE } from "@/types/design";
import { CustomPaletteModal } from "@/components/custom-palette-modal";

interface ColorPalettePickerProps {
  paletteId: string;
  customPalette: ColorSwatch | null;
  onSelect: (paletteId: string) => void;
  onCustomPaletteChange: (swatch: ColorSwatch) => void;
}

export function ColorPalettePicker({
  paletteId,
  customPalette,
  onSelect,
  onCustomPaletteChange,
}: ColorPalettePickerProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Theme mode</h3>
      <p className="mb-3 text-xs text-muted-foreground">
        Pick a starting palette — every page will use these colors consistently.
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {COLOR_PALETTES.map((opt) => (
          <PaletteTile
            key={opt.id}
            name={opt.name}
            colors={opt.colors}
            selected={paletteId === opt.id}
            onClick={() => onSelect(opt.id)}
          />
        ))}
        <PaletteTile
          name="Let AI decide"
          icon={<Sparkles className="h-4 w-4" />}
          selected={paletteId === AI_CHOICE_ID}
          onClick={() => onSelect(AI_CHOICE_ID)}
        />
        <PaletteTile
          name="Custom"
          icon={<PaletteIcon className="h-4 w-4" />}
          colors={paletteId === CUSTOM_ID ? customPalette ?? undefined : undefined}
          selected={paletteId === CUSTOM_ID}
          onClick={() => setModalOpen(true)}
        />
      </div>

      <CustomPaletteModal
        open={modalOpen}
        initialValue={customPalette ?? DEFAULT_CUSTOM_PALETTE}
        onCancel={() => setModalOpen(false)}
        onApply={(swatch) => {
          onCustomPaletteChange(swatch);
          setModalOpen(false);
        }}
      />
    </div>
  );
}

function PaletteTile({
  name,
  colors,
  icon,
  selected,
  onClick,
}: {
  name: string;
  colors?: ColorSwatch;
  icon?: ReactNode;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "overflow-hidden rounded-xl border text-left transition-colors",
        selected ? "border-primary ring-2 ring-primary/40" : "border-border hover:border-muted-foreground/40"
      )}
    >
      <div className="relative flex h-14 w-full">
        {colors ? (
          [colors.primary, colors.secondary, colors.background, colors.text].map((c, i) => (
            <span key={i} className="flex-1" style={{ backgroundColor: c }} />
          ))
        ) : (
          <span className="flex flex-1 items-center justify-center bg-muted text-muted-foreground">{icon}</span>
        )}
        {selected ? (
          <span className="absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground shadow">
            <Check className="h-3 w-3" />
          </span>
        ) : null}
      </div>
      <div className="px-2.5 py-2 text-xs font-medium">{name}</div>
    </button>
  );
}
