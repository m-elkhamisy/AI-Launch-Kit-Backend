import { NextRequest, NextResponse } from "next/server";
import { extractProfile } from "@/lib/profile-extraction";

export const maxDuration = 300;

const MAX_BYTES = 15 * 1024 * 1024;

export async function POST(req: NextRequest) {
  let formData: FormData;
  try {
    formData = await req.formData();
  } catch {
    return NextResponse.json(
      { message: "Expected multipart/form-data with a 'file' field." },
      { status: 400 }
    );
  }

  const file = formData.get("file");
  if (!file || !(file instanceof File)) {
    return NextResponse.json({ message: "No file was uploaded." }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json(
      { message: "File is too large — please upload something under 15MB." },
      { status: 400 }
    );
  }

  try {
    const buffer = Buffer.from(await file.arrayBuffer());
    const result = await extractProfile(buffer, file.name);
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to read the uploaded file.";
    return NextResponse.json({ message }, { status: 500 });
  }
}
