/**
 * Global throttle for every OpenRouter request in the app.
 *
 * All calls — text generation, image generation, image labeling — share ONE
 * API key, so they share one upstream rate limit. Before this, each call
 * site managed (or didn't manage) its own pacing: mockups fired N-way
 * parallel, page builds capped themselves at 2, profile-photo labeling
 * fired all-at-once. Any of those bursts could trip the provider's limit
 * even though every individual call was fine, and a burst in one code path
 * could get an unrelated code path 429'd.
 *
 * This queue is the single enforcement point instead:
 *   1. CONCURRENCY CAP — at most `maxConcurrent` requests in flight at once
 *      across the whole server process (default 2; set
 *      OPENROUTER_SEQUENTIAL=1 for strictly chained one-at-a-time calls).
 *   2. MIN START GAP — consecutive requests start at least `minGapMs` apart
 *      (default 250ms), so even within the cap there's never a same-instant
 *      burst.
 *   3. SHARED RATE-LIMIT COOLDOWN — when any call reports a 429, the queue
 *      pauses NEW request starts for that call's backoff window. Without
 *      this, the other in-flight worker would keep hammering the same limit
 *      while the throttled one politely waited.
 *
 * Call sites keep their natural parallel shape (Promise.all etc.) — the
 * queue serializes underneath, which is why this is safer than sprinkling
 * ad-hoc `await`s through the pipeline: no code path can forget to pace
 * itself.
 */

function readIntEnv(name: string, fallback: number, min: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n >= min ? n : fallback;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export class RequestQueue {
  readonly maxConcurrent: number;
  readonly minGapMs: number;

  private active = 0;
  private waiters: Array<() => void> = [];
  private lastStartAt = 0;
  private pausedUntil = 0;

  /** Total requests started since process start — cheap observability,
   * mirrors the CLI tool's call counter. */
  started = 0;

  constructor(opts: { maxConcurrent: number; minGapMs: number }) {
    this.maxConcurrent = Math.max(1, opts.maxConcurrent);
    this.minGapMs = Math.max(0, opts.minGapMs);
  }

  /**
   * Called by the retry layer when a request came back rate-limited (429).
   * Pauses all NEW request starts until the cooldown passes, so parallel
   * workers back off together instead of taking turns re-tripping the limit.
   */
  noteRateLimit(cooldownMs: number): void {
    const until = Date.now() + cooldownMs;
    if (until > this.pausedUntil) {
      this.pausedUntil = until;
      console.warn(
        `[openrouter-queue] rate limit reported — pausing new requests for ~${Math.round(cooldownMs / 1000)}s so retries don't re-trip it.`
      );
    }
  }

  private async acquire(): Promise<void> {
    // `while`, not `if`: a freshly-arrived caller can grab the slot between
    // release() waking this waiter and this waiter resuming, so re-check.
    while (this.active >= this.maxConcurrent) {
      await new Promise<void>((resolve) => this.waiters.push(resolve));
    }
    this.active++;
    // Enforce the start gap and any rate-limit cooldown. Loop because both
    // deadlines can move (another worker starting bumps lastStartAt; a 429
    // elsewhere bumps pausedUntil) while this one sleeps.
    for (;;) {
      const now = Date.now();
      const wait = Math.max(this.lastStartAt + this.minGapMs - now, this.pausedUntil - now);
      if (wait <= 0) break;
      await sleep(wait);
    }
    this.lastStartAt = Date.now();
    this.started++;
  }

  private release(): void {
    this.active--;
    const next = this.waiters.shift();
    if (next) next();
  }

  /** Runs `fn` once a slot is free and pacing allows. The slot is held for
   * the duration of the request only — retry backoffs happen OUTSIDE the
   * slot (in the caller), so a long backoff never blocks unrelated calls;
   * the shared cooldown above handles the "everyone should pause" case. */
  async run<T>(fn: () => Promise<T>): Promise<T> {
    await this.acquire();
    try {
      return await fn();
    } finally {
      this.release();
    }
  }
}

const sequentialFlag = process.env.OPENROUTER_SEQUENTIAL ?? "";
const forceSequential = sequentialFlag === "1" || /^true$/i.test(sequentialFlag);

/** One queue per server process — every OpenRouter code path imports this
 * same instance because every code path spends the same key's rate limit. */
export const openrouterQueue = new RequestQueue({
  maxConcurrent: forceSequential ? 1 : readIntEnv("OPENROUTER_MAX_CONCURRENT", 2, 1),
  minGapMs: readIntEnv("OPENROUTER_MIN_REQUEST_GAP_MS", 250, 0),
});
