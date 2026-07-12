import { v0 } from "v0-sdk";
import { describeApiError } from "@/lib/utils";
import { V0Result } from "@/types/generation";

type V0ChatShape = {
  id: string;
  webUrl: string;
  latestVersion?: {
    status?: string;
    demoUrl?: string | null;
    files?: Array<unknown>;
  } | null;
};

function toResult(chat: V0ChatShape): V0Result {
  const status = chat.latestVersion?.status;
  return {
    chatId: chat.id,
    webUrl: chat.webUrl,
    demoUrl: chat.latestVersion?.demoUrl ?? null,
    status: status === "completed" || status === "failed" ? status : "pending",
    fileCount: chat.latestVersion?.files?.length ?? 0,
  };
}

/**
 * "v0" provider mode: v0 generates the whole (possibly multi-page) site
 * itself from a written brief. No Claude HTML involved. The prompt is built
 * by lib/site-prompts.ts (buildV0MultiPageBrief) — this function just makes
 * the call.
 */
export async function generateWithV0(prompt: string): Promise<V0Result> {
  let chat;
  try {
    chat = await v0.chats.create({
      message: prompt,
      chatPrivacy: "private",
    });
  } catch (err) {
    throw new Error(describeApiError("v0", err));
  }

  // chats.create()'s type covers a streaming response too (only returned
  // when `responseMode: 'experimental_stream'` is requested, which we never
  // do here) — narrow it explicitly rather than asserting, so a future
  // change that does request streaming fails loudly here instead of
  // crashing deeper in toResult().
  if (!("id" in chat)) {
    throw new Error(
      "v0 returned a streaming chat response, which this pipeline doesn't handle."
    );
  }

  return toResult(chat);
}

/**
 * "both" provider mode: Claude already wrote the HTML for every page. Seed
 * v0 with those exact files, locked so v0 hosts them as-is instead of
 * rewriting them, and it gives us a shareable preview/deploy.
 */
export async function hostMultiPageWithV0(
  pages: Array<{ slug: string; html: string }>,
  companyName: string
): Promise<V0Result> {
  if (pages.length === 0) {
    throw new Error("hostMultiPageWithV0 called with no pages to host.");
  }

  let chat;
  try {
    chat = await v0.chats.init({
      type: "files",
      name: companyName ? `${companyName} — site` : undefined,
      chatPrivacy: "private",
      files: pages.map((p) => ({
        name: `${p.slug}.html`,
        content: p.html,
        // locked: true is what stops v0's model from rewriting this file on
        // a later pass — the whole point here is "host this exact HTML".
        locked: true,
      })),
    });
  } catch (err) {
    throw new Error(describeApiError("v0", err));
  }

  return toResult(chat);
}

export async function getV0ChatStatus(chatId: string): Promise<V0Result> {
  try {
    const chat = await v0.chats.getById({ chatId });
    return toResult(chat);
  } catch (err) {
    throw new Error(describeApiError("v0", err));
  }
}

export function isV0Configured(): boolean {
  return Boolean(process.env.V0_API_KEY);
}
