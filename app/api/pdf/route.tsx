import { NextRequest, NextResponse } from "next/server";
import { renderToBuffer } from "@react-pdf/renderer";
import { PdfDocument } from "@/lib/pdf-document";
import { OnboardingFormData } from "@/types/form";
import { DesignPrefs } from "@/types/design";
import { slugify } from "@/lib/utils";

interface Body {
  form: OnboardingFormData;
  design?: DesignPrefs;
}

export async function POST(req: NextRequest) {
  let body: Body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ message: "Invalid JSON body." }, { status: 400 });
  }
  if (!body.form) {
    return NextResponse.json({ message: "form is required." }, { status: 400 });
  }

  const element = <PdfDocument form={body.form} design={body.design} />;

  try {
    const buffer = await renderToBuffer(element);
    const filename = `${slugify(body.form.companyName || "brief")}-brief.pdf`;
    return new NextResponse(new Uint8Array(buffer), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to generate the PDF.";
    return NextResponse.json({ message }, { status: 500 });
  }
}
