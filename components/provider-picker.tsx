"use client";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { GenerationProvider } from "@/types/generation";

interface ProviderOption {
  value: GenerationProvider;
  title: string;
  description: string;
}

const OPTIONS: ProviderOption[] = [
  {
    value: "claude",
    title: "Claude (HTML)",
    description: "Claude writes every page as clean, self-contained HTML you can download and host anywhere.",
  },
  {
    value: "v0",
    title: "v0",
    description: "v0 builds the whole multi-page site directly as a live, hosted Next.js app.",
  },
  {
    value: "both",
    title: "Claude + v0",
    description: "Claude writes the HTML for full control, then v0 hosts those exact pages for an instant shareable link.",
  },
];

interface ProviderPickerProps {
  value: GenerationProvider;
  onChange: (value: GenerationProvider) => void;
}

export function ProviderPicker({ value, onChange }: ProviderPickerProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {OPTIONS.map((opt) => {
        const selected = value === opt.value;
        return (
          <Card
            key={opt.value}
            role="button"
            tabIndex={0}
            onClick={() => onChange(opt.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onChange(opt.value);
            }}
            className={cn(
              "cursor-pointer p-4 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              selected ? "border-primary bg-primary/5" : "hover:border-muted-foreground/40"
            )}
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="font-medium">{opt.title}</span>
              {selected ? <span className="text-xs text-primary">Selected</span> : null}
            </div>
            <p className="text-xs text-muted-foreground">{opt.description}</p>
          </Card>
        );
      })}
    </div>
  );
}
