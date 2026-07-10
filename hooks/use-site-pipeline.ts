"use client";

import { useCallback, useState } from "react";
import { EMPTY_FORM_DATA } from "@/lib/form-config";
import { OnboardingFormData, REQUIRED_FIELDS } from "@/types/form";
import { DesignPrefs, EMPTY_DESIGN_PREFS } from "@/types/design";
import {
  BuildRequestBody,
  ExtractedImage,
  GenerationProvider,
  MockupDesign,
  MockupsResponseBody,
  PipelineResult,
  PlanRequestBody,
  PlanResponseBody,
  ProfileExtractionResult,
  SitePlan,
  WizardStep,
} from "@/types/generation";

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `Request to ${url} failed.`);
  }
  return data as T;
}

export function useSitePipeline() {
  const [step, setStep] = useState<WizardStep>("intake");
  const [form, setForm] = useState<OnboardingFormData>(EMPTY_FORM_DATA);
  const [design, setDesign] = useState<DesignPrefs>(EMPTY_DESIGN_PREFS);
  const [provider, setProvider] = useState<GenerationProvider>("claude");
  const [uploadedImages, setUploadedImages] = useState<ExtractedImage[]>([]);

  const [mockups, setMockups] = useState<MockupDesign[]>([]);
  const [chosenMockup, setChosenMockup] = useState<MockupDesign | null>(null);
  const [plan, setPlan] = useState<SitePlan | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canProceedFromIntake = REQUIRED_FIELDS.every((f) => form[f].trim().length > 0);

  const applyProfileExtraction = useCallback((extraction: ProfileExtractionResult) => {
    setForm((prev) => {
      const next = { ...prev };
      (Object.keys(extraction.fields) as Array<keyof OnboardingFormData>).forEach((key) => {
        const v = extraction.fields[key];
        if (v && v.trim()) next[key] = v;
      });
      return next;
    });
    setDesign((prev) => ({
      ...prev,
      tagline: extraction.designHints.tagline || prev.tagline,
      cta: extraction.designHints.cta || prev.cta,
      imageSource: extraction.images.length > 0 ? "uploaded" : prev.imageSource,
    }));
    if (extraction.images.length > 0) {
      setUploadedImages((prev) => [...prev, ...extraction.images]);
    }
  }, []);

  const generateMockups = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await postJson<MockupsResponseBody>("/api/site/mockups", {
        form,
        design,
        uploadedImages,
      });
      setMockups(data.mockups);
      setStep("mockups");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate mockups.");
    } finally {
      setLoading(false);
    }
  }, [form, design, uploadedImages]);

  const requestPlan = useCallback(
    async (mockup: MockupDesign, feedback?: string, previousPlan?: SitePlan) => {
      setLoading(true);
      setError(null);
      try {
        const body: PlanRequestBody = {
          form,
          design,
          chosenMockupHtml: mockup.html,
          feedback,
          previousPlan,
        };
        const data = await postJson<PlanResponseBody>("/api/site/plan", body);
        setPlan(data.plan);
        setStep("plan");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to generate the site plan.");
      } finally {
        setLoading(false);
      }
    },
    [form, design]
  );

  const chooseMockup = useCallback(
    (mockup: MockupDesign) => {
      setChosenMockup(mockup);
      void requestPlan(mockup);
    },
    [requestPlan]
  );

  const revisePlan = useCallback(
    (feedback: string) => {
      if (!chosenMockup) return;
      void requestPlan(chosenMockup, feedback, plan ?? undefined);
    },
    [chosenMockup, plan, requestPlan]
  );

  const approvePlanAndBuild = useCallback(
    async (finalPlan: SitePlan) => {
      if (!chosenMockup) return;
      setPlan(finalPlan);
      setStep("building");
      setLoading(true);
      setError(null);
      try {
        const body: BuildRequestBody = {
          form,
          design,
          provider,
          chosenMockupHtml: chosenMockup.html,
          plan: finalPlan,
          uploadedImages,
        };
        const data = await postJson<PipelineResult>("/api/site/build", body);
        setResult(data);
        setStep("results");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to build the site.");
        setStep("plan");
      } finally {
        setLoading(false);
      }
    },
    [chosenMockup, form, design, provider, uploadedImages]
  );

  const reset = useCallback(() => {
    setStep("intake");
    setForm(EMPTY_FORM_DATA);
    setDesign(EMPTY_DESIGN_PREFS);
    setProvider("claude");
    setUploadedImages([]);
    setMockups([]);
    setChosenMockup(null);
    setPlan(null);
    setResult(null);
    setError(null);
  }, []);

  return {
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
    chosenMockup,
    plan,
    result,
    loading,
    error,
    generateMockups,
    chooseMockup,
    revisePlan,
    approvePlanAndBuild,
    reset,
  };
}
