"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { ANIMATION_OPTIONS, DesignPrefs, STYLE_OPTIONS, THEME_OPTIONS } from "@/types/design";

function PillGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={cn(
            "rounded-full border px-3 py-1.5 text-xs transition-colors",
            value === opt
              ? "border-primary bg-primary text-primary-foreground"
              : "border-input bg-transparent text-foreground hover:bg-accent"
          )}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

interface ImageSourceOption {
  value: DesignPrefs["imageSource"];
  label: string;
  description: string;
  disabled?: boolean;
}

interface DesignPrefsFormProps {
  value: DesignPrefs;
  onChange: (value: DesignPrefs) => void;
  hasUploadedImages: boolean;
}

export function DesignPrefsForm({ value, onChange, hasUploadedImages }: DesignPrefsFormProps) {
  function set<K extends keyof DesignPrefs>(key: K, v: DesignPrefs[K]) {
    onChange({ ...value, [key]: v });
  }

  const imageSourceOptions: ImageSourceOption[] = [
    {
      value: "uploaded",
      label: "Your uploaded photos",
      description: "Real photos pulled from your company profile document.",
      disabled: !hasUploadedImages,
    },
    { value: "pexels", label: "Stock photos", description: "Real stock photography, licensed and free to use." },
    { value: "ai", label: "AI-generated", description: "Custom photorealistic images generated for this brand." },
    { value: "placeholder", label: "Styled placeholders", description: "No photos — clean gradient/color panels instead." },
  ];

  return (
    <div className="space-y-6">
      <div>
        <Label className="mb-2 block text-sm">Design category</Label>
        <PillGroup options={STYLE_OPTIONS} value={value.style} onChange={(v) => set("style", v)} />
      </div>
      <div>
        <Label className="mb-2 block text-sm">How much animation?</Label>
        <PillGroup options={ANIMATION_OPTIONS} value={value.animation} onChange={(v) => set("animation", v)} />
      </div>
      <div>
        <Label className="mb-2 block text-sm">Theme mode</Label>
        <PillGroup options={THEME_OPTIONS} value={value.theme} onChange={(v) => set("theme", v)} />
      </div>

      <div>
        <Label className="mb-2 block text-sm">Where should photos come from?</Label>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {imageSourceOptions.map((opt) => (
            <button
              key={opt.value}
              type="button"
              disabled={opt.disabled}
              onClick={() => set("imageSource", opt.value)}
              className={cn(
                "rounded-lg border p-3 text-left text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40",
                value.imageSource === opt.value
                  ? "border-primary bg-primary/5"
                  : "border-input hover:bg-accent"
              )}
            >
              <div className="mb-0.5 font-medium text-foreground">{opt.label}</div>
              <div className="text-muted-foreground">
                {opt.disabled ? "Upload a company profile (DOCX) first to unlock this." : opt.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="tagline" className="mb-1.5 block text-sm">
            Tagline / hero message
          </Label>
          <Input
            id="tagline"
            value={value.tagline}
            placeholder="Leave blank to let the AI write one from your UVP"
            onChange={(e) => set("tagline", e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="cta" className="mb-1.5 block text-sm">
            Main call-to-action
          </Label>
          <Input
            id="cta"
            value={value.cta}
            placeholder="e.g. Order Now, Book a Call"
            onChange={(e) => set("cta", e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
