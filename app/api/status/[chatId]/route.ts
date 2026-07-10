import { NextRequest, NextResponse } from "next/server";
import { getV0ChatStatus } from "@/lib/v0";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ chatId: string }> }
) {
  const { chatId } = await params;

  if (!chatId) {
    return NextResponse.json({ message: "chatId is required." }, { status: 400 });
  }

  try {
    const result = await getV0ChatStatus(chatId);
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to fetch status.";
    return NextResponse.json({ message }, { status: 500 });
  }
}
