export interface OnboardingFormData {
  // identity
  companyName: string;
  industry: string;
  activityCode: string;
  businessActivity: string;
  // audience & positioning
  targetAudience: string;
  uvp: string;
  competitors: string;
  purpose: string;
  // proof & facts — deliberately its own section. Left blank, these stay
  // blank in the generated site rather than being invented by the model.
  // See lib/grounding.ts for how this feeds the anti-hallucination rules.
  stats: string;
  testimonials: string;
  teamBios: string;
  certifications: string;
  // practical details
  products: string;
  locationHours: string;
  serviceArea: string;
  contact: string;
  socials: string;
  // voice
  tone: string;
  aesthetic: string;
  // extra
  description: string;
  notes: string;
}

export type OnboardingFormField = keyof OnboardingFormData;

export interface FormFieldConfig {
  key: OnboardingFormField;
  label: string;
  placeholder: string;
  type: "input" | "textarea";
  maxLength?: number;
  required?: boolean;
  helpText?: string;
  section: "identity" | "audience" | "proof" | "practical" | "voice" | "extra";
}

export const REQUIRED_FIELDS: OnboardingFormField[] = [
  "companyName",
  "industry",
  "businessActivity",
  "targetAudience",
  "uvp",
];
