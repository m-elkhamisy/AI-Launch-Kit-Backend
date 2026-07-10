import { NextRequest, NextResponse } from "next/server";
import { BuildRequestBody, BuildResponseBody } from "@/types/generation";
import { runBuild } from "@/lib/site-pipeline";

export const maxDuration = 300;

export async function POST(req: NextRequest) {
  let body: BuildRequestBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ message: "Invalid JSON body." }, { status: 400 });
  }
  if (!body.plan?.pages?.length) {
    return NextResponse.json({ message: "plan.pages is required and must be non-empty." }, { status: 400 });
  }

  try {
    const result: BuildResponseBody = await runBuild(
      body.form,
      body.design,
      body.provider,
      body.chosenMockupHtml,
      body.plan,
      body.uploadedImages ?? []
    );
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to build the site.";
    return NextResponse.json({ message }, { status: 500 });
  }
}
