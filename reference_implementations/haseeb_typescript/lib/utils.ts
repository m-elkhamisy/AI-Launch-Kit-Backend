import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Turns a company name into a safe filename fragment, e.g. for downloads. */
export function slugify(value: string): string {
  return (
    value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "") || "site"
  );
}

/**
 * Like Promise.all(items.map(fn)), but runs at most `limit` at a time.
 * The multi-page build used to fire every remaining page at OpenRouter in
 * one unbounded Promise.all — fine for 3-4 pages most of the time, but each
 * page asks for up to 16k output tokens, so a 4-5 page plan can demand
 * 60-80k+ tokens from the same upstream provider within a couple seconds.
 * That's a common trigger for a provider-side rate limit even when the
 * account/key/model are all fine. Capping concurrency spreads that load out.
 */
export async function mapWithConcurrency<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;

  async function worker() {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  }

  const workerCount = Math.max(1, Math.min(limit, items.length));
  await Promise.all(Array.from({ length: workerCount }, worker));
  return results;
}

/**
 * Both the OpenRouter (openai) and v0-sdk clients parse their HTTP response
 * as JSON internally. If the upstream service returns something that isn't
 * valid JSON — an empty body on a timeout, an HTML error/rate-limit page, a
 * dropped connection mid-response — the SDK's own `JSON.parse` throws, and
 * the message that reaches us is a bare, contextless
 * "Unexpected end of JSON input" (or "Unexpected token ... in JSON").
 * That's technically correct but useless to read in the UI: it gives no
 * hint that the brief was fine and the *provider* is what hiccuped. This
 * wraps any such error with the provider name and a plain-language reason,
 * while still keeping the original message for debugging.
 */
export function describeApiError(provider: string, err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  const looksLikeUnreadableResponse =
    /unexpected end of json input|unexpected token .* in json|failed to fetch|fetch failed|network|ECONNRESET|ETIMEDOUT/i.test(
      raw
    );

  if (looksLikeUnreadableResponse) {
    return (
      `${provider} sent back a response that couldn't be read — usually a timeout, ` +
      `an invalid or expired API key, a rate limit, or a brief outage on their end, ` +
      `rather than anything wrong with your brief. Try again in a moment. (Raw error: ${raw})`
    );
  }

  return `${provider} request failed: ${raw}`;
}
