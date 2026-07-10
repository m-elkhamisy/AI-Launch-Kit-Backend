import { NextRequest, NextResponse } from "next/server";
import { PlanRequestBody, PlanResponseBody } from "@/types/generation";
import { generateSitePlan, prepareBrief } from "@/lib/site-pipeline";

export const maxDuration = 300;

export async function POST(req: NextRequest) {
  let body: PlanRequestBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ message: "Invalid JSON body." }, { status: 400 });
  }
  if (!body.chosenMockupHtml) {
    return NextResponse.json({ message: "chosenMockupHtml is required." }, { status: 400 });
  }

  try {
    const brief = await prepareBrief(body.form, body.design);
    const plan = await generateSitePlan(brief, body.chosenMockupHtml, body.feedback, body.previousPlan);
    const response: PlanResponseBody = { plan };
    return NextResponse.json(response);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to generate the site plan.";
    return NextResponse.json({ message }, { status: 500 });
  }
}
