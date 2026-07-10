"use client";

import { ColorPalettePicker } from "@/components/color-palette-picker";
import { FontPairingPicker } from "@/components/font-pairing-picker";
import { DesignPrefs } from "@/types/design";

interface ColorsFontsStepProps {
  value: DesignPrefs;
  onChange: (value: DesignPrefs) => void;
}

export function ColorsFontsStep({ value, onChange }: ColorsFontsStepProps) {
  return (
    <div className="space-y-10">
      <ColorPalettePicker
        paletteId={value.paletteId}
        customPalette={value.customPalette}
        onSelect={(paletteId) => onChange({ ...value, paletteId })}
        onCustomPaletteChange={(customPalette) => onChange({ ...value, paletteId: "custom", customPalette })}
      />
      <FontPairingPicker
        fontPairingId={value.fontPairingId}
        customFonts={value.customFonts}
        onSelect={(fontPairingId) => onChange({ ...value, fontPairingId })}
        onCustomFontsChange={(customFonts) => onChange({ ...value, fontPairingId: "custom", customFonts })}
      />
    </div>
  );
}
