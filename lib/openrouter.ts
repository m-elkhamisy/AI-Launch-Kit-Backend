
import "server-only";

import OpenAI from "openai";

const apiKey = process.env.OPENROUTER_API_KEY;

export const openrouter = new OpenAI({
  baseURL: "https://openrouter.ai/api/v1",
  apiKey: apiKey || "missing-openrouter-api-key",
  defaultHeaders: {
    "HTTP-Referer": process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
    "X-Title": "LaunchKit Generator",
  },
});

export function assertOpenRouterConfigured() {
  if (!apiKey) {
    throw new Error(
      "OPENROUTER_API_KEY is not set. Add it to .env.local — see .env.example."
    );
  }
}

/** One model config, used for planning, mockups, page builds, and profile
 * extraction. Previously split into separate KARIM_MODEL / HASEEB defaults
 * that quietly drifted apart — now a single override point. */
export const GENERATION_MODEL =
  process.env.GENERATION_MODEL || "anthropic/claude-sonnet-5";

/** Cheaper/faster calls: image labeling, quick JSON field extraction.
 * Defaults to the same model — split it out via env if you want a cheaper
 * one for utility calls specifically. */
export const UTILITY_MODEL = process.env.UTILITY_MODEL || GENERATION_MODEL;

/** AI photo generation (used when the person picks "AI-generated" as the
 * image source). Kept cheap by default. */
export const IMAGE_MODEL =
  process.env.IMAGE_MODEL || "google/gemini-2.5-flash-image";

/** Strips ```json / ``` fences models sometimes wrap structured output in. */
export function stripCodeFence(raw: string): string {
  return raw
    .trim()
    .replace(/^```(?:json|html|jsx|tsx)?\s*/i, "")
    .replace(/\s*```$/i, "");
}

interface OpenRouterErrorBody {
  error?: {
    message?: string;
    code?: unknown;
    type?: string;
    // OpenRouter's own wrapper text (e.g. "Provider returned error") is
    // usually a red herring — the *actual* reason lives one level down in
    // metadata, which the code used to ignore entirely.
    metadata?: { raw?: string; provider_name?: string };
  };
}

/** HTTP-style codes worth retrying: rate limits and transient upstream
 * failures. Anything else (bad key, bad request, model not found) will
 * fail the same way every time, so retrying just burns 5-10s for nothing. */
const RETRYABLE_CODES = new Set([429, 500, 502, 503, 504]);

/**
 * Thrown by firstChoiceOrThrow. Carries the parsed OpenRouter error code (if
 * any) so callers — specifically callClaude's retry loop — can tell a
 * worth-retrying rate limit/outage apart from a request that will never
 * succeed, instead of retrying (or not) blindly.
 */
export class OpenRouterCallError extends Error {
  code?: number;
  providerName?: string;

  constructor(message: string, opts: { code?: number; providerName?: string } = {}) {
    super(message);
    this.name = "OpenRouterCallError";
    this.code = opts.code;
    this.providerName = opts.providerName;
  }

  get isRetryable(): boolean {
    // No parsed code at all (e.g. a network-level hiccup) — give it the
    // benefit of the doubt and retry once too.
    return this.code === undefined || RETRYABLE_CODES.has(this.code);
  }
}

function describeOpenRouterFailure(response: unknown, context: string): OpenRouterCallError {
  const r = response as OpenRouterErrorBody | undefined;
  const err = r?.error;
  if (err?.message) {
    const code = Number(err.code);
    const provider = err.metadata?.provider_name;
    const raw = err.metadata?.raw;
    const providerPart = provider ? ` [provider: ${provider}]` : "";
    const codePart = Number.isFinite(code) ? ` [code ${code}]` : "";
    const rawPart = raw && raw !== err.message ? ` Upstream said: ${raw}` : "";
    return new OpenRouterCallError(
      `OpenRouter error during ${context}${providerPart}${codePart}: ${err.message}.${rawPart} ` +
        `Check OPENROUTER_API_KEY, that your OpenRouter account has credits, and that the model slug is available on your account.`,
      { code: Number.isFinite(code) ? code : undefined, providerName: provider }
    );
  }
  return new OpenRouterCallError(
    `OpenRouter returned no usable response during ${context} (no choices in the reply). ` +
      `This usually means a rate limit, an invalid/missing API key, or an unavailable model — ` +
      `it tends to show up under a burst of parallel calls (like a multi-page build) even when a single call worked fine.`
  );
}

/**
 * Every OpenRouter chat completion in this project must read its response
 * through this instead of indexing `response.choices[0]` directly.
 * OpenRouter can return HTTP 200 with an `{error: {...}}` body — no
 * `choices` field at all — when the upstream provider call fails (bad key,
 * no credits, rate limit, model unavailable). Indexing `[0]` straight into
 * a missing `choices` throws "Cannot read properties of undefined (reading
 * '0')", which is accurate but useless to act on — this throws an
 * OpenRouterCallError with the real code/provider instead.
 */
export function firstChoiceOrThrow<TMessage = unknown>(response: unknown, context: string): TMessage {
  const r = response as { choices?: Array<{ message?: TMessage }> } | undefined;
  const message = r?.choices?.[0]?.message;
  if (!message) {
    throw describeOpenRouterFailure(response, context);
  }
  return message;
}
