"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ProfileUpload } from "@/components/profile-upload";
import { IntakeForm } from "@/components/intake-form";
import { DesignPrefsForm } from "@/components/design-prefs-form";
import { ColorsFontsStep } from "@/components/colors-fonts-step";
import { ProviderPicker } from "@/components/provider-picker";
import { MockupGallery } from "@/components/mockup-gallery";
import { PlanReview } from "@/components/plan-review";
import { SiteResults } from "@/components/site-results";
import { PipelineProgress } from "@/components/pipeline-progress";
import { useSitePipeline } from "@/hooks/use-site-pipeline";
import { MOCKUP_COUNT } from "@/types/generation";

export function SiteWizard() {
  const pipeline = useSitePipeline();
  const {
    step,
    setStep,
    form,
    setForm,
    design,
    setDesign,
    provider,
    setProvider,
    uploadedImages,
    applyProfileExtraction,
    canProceedFromIntake,
    mockups,
    plan,
    result,
    loading,
    error,
    generateMockups,
    chooseMockup,
    revisePlan,
    approvePlanAndBuild,
    reset,
  } = pipeline;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold">LaunchKit Generator</h1>
        <p className="text-sm text-muted-foreground">
          Turn a client brief into a finished marketing website — pick Claude, v0, or both.
        </p>
      </div>

      {step !== "intake" ? <PipelineProgress step={step} provider={provider} /> : null}

      {error ? (
        <Card className="mb-5 border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </Card>
      ) : null}

      {step === "intake" ? (
        <div className="space-y-6">
          <ProfileUpload onExtracted={applyProfileExtraction} />
          <IntakeForm value={form} onChange={setForm} />
          <div className="flex justify-end border-t pt-5">
            <Button disabled={!canProceedFromIntake} onClick={() => setStep("design")}>
              Continue
            </Button>
          </div>
        </div>
      ) : null}

      {step === "design" ? (
        <div className="space-y-8">
          <DesignPrefsForm value={design} onChange={setDesign} hasUploadedImages={uploadedImages.length > 0} />
          <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              How should this be generated?
            </h3>
            <ProviderPicker value={provider} onChange={setProvider} />
          </div>
          <div className="flex justify-between border-t pt-5">
            <Button variant="ghost" onClick={() => setStep("intake")}>
              Back
            </Button>
            <Button onClick={() => setStep("colors")}>Continue</Button>
          </div>
        </div>
      ) : null}

      {step === "colors" ? (
        <div className="space-y-8">
          <ColorsFontsStep value={design} onChange={setDesign} />
          <div className="flex justify-between border-t pt-5">
            <Button variant="ghost" onClick={() => setStep("design")}>
              Back
            </Button>
            <Button disabled={loading} onClick={generateMockups}>
              {loading ? "Designing…" : `Generate ${MOCKUP_COUNT} designs`}
            </Button>
          </div>
        </div>
      ) : null}

      {step === "mockups" ? (
        <div className="space-y-5">
          <p className="text-sm text-muted-foreground">Pick the direction that fits the brand best.</p>
          <MockupGallery mockups={mockups} onChoose={chooseMockup} busy={loading} />
          <div className="border-t pt-5">
            <Button variant="ghost" onClick={() => setStep("colors")}>
              Back
            </Button>
          </div>
        </div>
      ) : null}

      {step === "plan" && plan ? (
        <div className="space-y-5">
          <PlanReview plan={plan} busy={loading} onApprove={approvePlanAndBuild} onRevise={revisePlan} />
          <div className="border-t pt-5">
            <Button variant="ghost" onClick={() => setStep("mockups")} disabled={loading}>
              Back
            </Button>
          </div>
        </div>
      ) : null}

      {step === "building" ? (
        <Card className="flex flex-col items-center justify-center gap-3 p-16 text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">
            This can take a couple of minutes for a full multi-page site — hang tight.
          </p>
        </Card>
      ) : null}

      {step === "results" && result ? (
        <SiteResults result={result} form={form} design={design} onStartOver={reset} />
      ) : null}
    </div>
  );
}
