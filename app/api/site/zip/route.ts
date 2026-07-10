import { NextRequest, NextResponse } from "next/server";
import JSZip from "jszip";
import { ZipRequestBody } from "@/types/generation";
import { slugify } from "@/lib/utils";

export async function POST(req: NextRequest) {
  let body: ZipRequestBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ message: "Invalid JSON body." }, { status: 400 });
  }
  if (!body.pages || body.pages.length === 0) {
    return NextResponse.json({ message: "pages is required and must be non-empty." }, { status: 400 });
  }

  const zip = new JSZip();
  for (const page of body.pages) {
    zip.file(page.filename, page.html);
  }
  const buffer = await zip.generateAsync({ type: "nodebuffer" });
  const filename = `${slugify(body.companyName || "site")}.zip`;

  return new NextResponse(new Uint8Array(buffer), {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${filename}"`,
    },
  });
}
