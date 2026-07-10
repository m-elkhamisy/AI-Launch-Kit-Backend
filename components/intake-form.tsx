"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { fieldsForSection, SECTION_LABELS } from "@/lib/form-config";
import { SECTION_ORDER } from "@/lib/form-config";
import { OnboardingFormData } from "@/types/form";

interface IntakeFormProps {
  value: OnboardingFormData;
  onChange: (value: OnboardingFormData) => void;
}

export function IntakeForm({ value, onChange }: IntakeFormProps) {
  function setField(key: keyof OnboardingFormData, fieldValue: string) {
    onChange({ ...value, [key]: fieldValue });
  }

  return (
    <div className="space-y-8">
      {SECTION_ORDER.map((section, sIdx) => {
        const fields = fieldsForSection(section);
        const meta = SECTION_LABELS[section];
        return (
          <div key={section}>
            {sIdx > 0 ? <Separator className="mb-8" /> : null}
            <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {meta.title}
            </h3>
            {meta.helpText ? <p className="mb-4 text-xs text-muted-foreground">{meta.helpText}</p> : null}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              {fields.map((field) => (
                <div
                  key={field.key}
                  className={field.type === "textarea" ? "sm:col-span-2" : undefined}
                >
                  <Label htmlFor={field.key} className="mb-1.5 block text-sm">
                    {field.label}
                    {field.required ? <span className="ml-1 text-destructive">*</span> : null}
                  </Label>
                  {field.type === "textarea" ? (
                    <Textarea
                      id={field.key}
                      value={value[field.key]}
                      placeholder={field.placeholder}
                      onChange={(e) => setField(field.key, e.target.value)}
                      rows={3}
                    />
                  ) : (
                    <Input
                      id={field.key}
                      value={value[field.key]}
                      placeholder={field.placeholder}
                      onChange={(e) => setField(field.key, e.target.value)}
                    />
                  )}
                  {field.helpText ? (
                    <p className="mt-1 text-xs text-muted-foreground">{field.helpText}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
