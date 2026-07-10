import { NextRequest, NextResponse } from "next/server";
import { slugify } from "@/lib/utils";

export async function POST(req: NextRequest) {
  let body: { html?: string; companyName?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ message: "Invalid JSON body." }, { status: 400 });
  }

  if (!body.html) {
    return NextResponse.json({ message: "html is required." }, { status: 400 });
  }

  const filename = `${slugify(body.companyName ?? "site")}.html`;

  return new NextResponse(body.html, {
    status: 200,
    headers: {
      "Content-Type": "text/html",
      "Content-Disposition": `attachment; filename="${filename}"`,
    },
  });
}
