"use client";

import { cn } from "@/lib/utils";
import { GenerationProvider, STEP_ORDER, WizardStep } from "@/types/generation";

const STEP_LABELS: Record<WizardStep, string> = {
  intake: "Business",
  design: "Design Category & Mood",
  colors: "Colors & Fonts",
  mockups: "Pick a design",
  plan: "Pick Pages",
  building: "Build",
  results: "Your site",
};

const PROVIDER_LABELS: Record<GenerationProvider, string> = {
  v0: "v0 is building your multi-page site",
  claude: "Claude is writing each page",
  both: "Claude is writing each page, then handing off to v0",
};

interface PipelineProgressProps {
  step: WizardStep;
  provider: GenerationProvider;
}

export function PipelineProgress({ step, provider }: PipelineProgressProps) {
  const currentIndex = STEP_ORDER.indexOf(step);

  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center gap-1">
        {STEP_ORDER.map((s, i) => (
          <div key={s} className="flex flex-1 items-center gap-1">
            <div
              className={cn(
                "h-1.5 flex-1 rounded-full",
                i <= currentIndex ? "bg-primary" : "bg-muted"
              )}
            />
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{STEP_LABELS[step]}</span>
        {step === "building" ? <span className="animate-pulse">{PROVIDER_LABELS[provider]}…</span> : null}
      </div>
    </div>
  );
}
