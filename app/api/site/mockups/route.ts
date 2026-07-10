import { NextRequest, NextResponse } from "next/server";
import { OnboardingFormData, REQUIRED_FIELDS } from "@/types/form";
import { DesignPrefs } from "@/types/design";
import { ExtractedImage, MockupsResponseBody } from "@/types/generation";
import { generateMockupDesigns } from "@/lib/site-pipeline";

export const maxDuration = 300;

interface Body {
  form: OnboardingFormData;
  design: DesignPrefs;
  uploadedImages?: ExtractedImage[];
}

export async function POST(req: NextRequest) {
  let body: Body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ message: "Invalid JSON body." }, { status: 400 });
  }

  const missing = REQUIRED_FIELDS.filter((f) => !body.form?.[f]?.trim());
  if (missing.length > 0) {
    return NextResponse.json(
      { message: `Missing required field(s): ${missing.join(", ")}` },
      { status: 400 }
    );
  }

  try {
    const { mockups } = await generateMockupDesigns(body.form, body.design, body.uploadedImages ?? []);
    const response: MockupsResponseBody = { mockups };
    return NextResponse.json(response);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to generate mockups.";
    return NextResponse.json({ message }, { status: 500 });
  }
}
