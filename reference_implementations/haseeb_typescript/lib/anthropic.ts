import "server-only";

import {
  openrouter,
  GENERATION_MODEL,
  UTILITY_MODEL,
  stripCodeFence,
  assertOpenRouterConfigured,
  firstChoiceOrThrow,
  OpenRouterCallError,
} from "./openrouter";
import { openrouterQueue } from "./request-queue";
import { SiteCopy } from "@/types/generation";

export interface ClaudeCallOptions {
  maxTokens?: number;
  model?: string;
  temperature?: number;
}

async function callClaudeOnce(prompt: string, opts: ClaudeCallOptions): Promise<string> {
  const model = opts.model || GENERATION_MODEL;
  const response = await openrouter.chat.completions.create({
    model,
    max_tokens: opts.maxTokens ?? 4000,
    temperature: opts.temperature,
    messages: [{ role: "user", content: prompt }],
  });
  const message = firstChoiceOrThrow<{ content?: unknown }>(response, `text generation (${model})`);
  const content = message.content;
  if (typeof content !== "string" || !content) {
    throw new Error(`${model} returned an empty response.`);
  }
  return content;
}

const MAX_ATTEMPTS = 6;

/** attempt 0 -> ~1s, 1 -> ~2s, 2 -> ~4s, plus up to 400ms of jitter so
 * several pages throttled by the same burst don't all retry in lockstep
 * and re-trip the same rate limit together. */
function backoffDelayMs(attempt: number): number {
  return 1000 * 2 ** attempt + Math.random() * 400;
}

export async function callClaude(
  prompt: string,
  opts: ClaudeCallOptions = {}
): Promise<string> {
  assertOpenRouterConfigured();
  let lastErr: unknown;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    try {
      // Every attempt goes through the shared queue, so no matter how many
      // pages/mockups/labels are requested in parallel upstream, requests
      // reach OpenRouter paced and capped. The queue slot is held only for
      // the request itself — the backoff sleep below happens outside it.
      return await openrouterQueue.run(() => callClaudeOnce(prompt, opts));
    } catch (err) {
      lastErr = err;
      // A bad key / bad model slug / malformed request fails identically
      // every time — burning three more attempts and ~10s of backoff on
      // those just delays showing the user an error they can't fix by
      // waiting. Only rate limits (429) and transient upstream failures
      // (5xx) are worth retrying.
      const retryable = err instanceof OpenRouterCallError ? err.isRetryable : true;
      if (!retryable || attempt === MAX_ATTEMPTS - 1) {
        throw err;
      }
      const delay = backoffDelayMs(attempt);
      // A 429 means the whole key is throttled, not just this call — tell
      // the queue so other workers stop starting new requests into the same
      // limit while this one backs off.
      if (err instanceof OpenRouterCallError && err.code === 429) {
        openrouterQueue.noteRateLimit(delay);
      }
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
}

export async function callClaudeJSON<T>(
  prompt: string,
  opts: ClaudeCallOptions = {}
): Promise<T> {
  const raw = await callClaude(prompt, {
    model: UTILITY_MODEL,
    maxTokens: 2000,
    ...opts,
  });
  const cleaned = stripCodeFence(raw);
  try {
    return JSON.parse(cleaned) as T;
  } catch {
    throw new Error(
      `Model returned invalid JSON, expected a parseable object: ${cleaned.slice(0, 300)}`
    );
  }
}

const HTML_MAX_TOKENS = 32000;

/** Default threshold matches the CLI tool's mockup check (~1200 chars); full
 * site pages pass a higher bar (~2500) via generateHtmlPage's options. */
const DEFAULT_MIN_CHARS = 1200;

/**
 * A generated document counts as complete when it (a) starts as a real HTML
 * document, (b) actually closed itself, and (c) contains a visible headline
 * and enough content to not be an empty shell. (b)+(c) catch the two real
 * failure modes the old DOCTYPE/</html> check missed: a syntactically-closed
 * page with a blank body, and a page whose "content" is one apology line.
 */
export function htmlLooksComplete(html: string, minChars = DEFAULT_MIN_CHARS): boolean {
  const trimmed = html.trim();
  if (trimmed.length < minChars) return false;
  if (!/^<!DOCTYPE/i.test(trimmed)) return false;
  if (!/<\/html>/i.test(trimmed) && !/<\/body>/i.test(trimmed)) return false;
  if (!/<h[12][\s>]/i.test(trimmed)) return false;
  return true;
}

export interface HtmlPageOptions {
  maxTokens?: number;
  /** Minimum character count for the page to be considered complete. */
  minChars?: number;
}

/**
 * Generates one self-contained HTML page. If the output is incomplete —
 * truncated mid-tag (common near the token ceiling on image-heavy pages),
 * missing its headline, or suspiciously short — retries once with an
 * explicit "finish the document, be more concise" nudge instead of silently
 * shipping a broken page. Callers that need a guaranteed render (mockups)
 * check htmlLooksComplete again afterwards and substitute a deterministic
 * fallback.
 */
export async function generateHtmlPage(
  prompt: string,
  opts: HtmlPageOptions = {}
): Promise<string> {
  const maxTokens = opts.maxTokens ?? HTML_MAX_TOKENS;
  const minChars = opts.minChars ?? DEFAULT_MIN_CHARS;

  const raw = await callClaude(prompt, { maxTokens });
  let html = stripCodeFence(raw);
  if (htmlLooksComplete(html, minChars)) return html;

  const retryPrompt = `${prompt}

IMPORTANT: your previous attempt was incomplete — it was cut off before the
closing </html> tag, or shipped without a real visible headline/content.
Return the COMPLETE single HTML file, from <!DOCTYPE html> to </html>, with a
real <h1> headline and real copy, and nothing else. Trim copy slightly if you
need to in order to fit — a shorter COMPLETE page beats a longer broken one.`;
  const retryRaw = await callClaude(retryPrompt, { maxTokens });
  html = stripCodeFence(retryRaw);
  return html;
}

/**
 * Pulls a short structured summary of already-generated copy for the PDF
 * brief. This only reflects what's already on the page — it must not add
 * anything not present in the HTML, so the PDF can't introduce new
 * hallucinated claims that never went through FACT_DISCIPLINE.
 */
export async function extractSiteCopy(homepageHtml: string): Promise<SiteCopy | null> {
  const prompt = `Read this HTML homepage and extract ONLY copy that is
literally present in the markup — do not paraphrase into something more
impressive, do not add anything. Return ONLY valid JSON, no markdown:
{"headline":"the exact or near-exact main H1 text","subheadline":"the hero subline text","sections":[{"heading":"...","body":"one sentence pulled from that section, in the page's own words"}],"callToAction":"the primary CTA button text"}
Include at most 4 sections. If you can't find a clear value for a field, use "".

HTML:
${homepageHtml.slice(0, 12000)}`;
  try {
    return await callClaudeJSON<SiteCopy>(prompt, { maxTokens: 1200 });
  } catch {
    return null;
  }
}
