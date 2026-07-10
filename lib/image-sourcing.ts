import { openrouter, IMAGE_MODEL, firstChoiceOrThrow } from "@/lib/openrouter";
import { openrouterQueue } from "@/lib/request-queue";
import { DesignPrefs } from "@/types/design";
import { ExtractedImage, PlannedPageImage } from "@/types/generation";

export interface SourcedImage {
  section: string;
  desc: string;
  src: string; // https URL (Pexels) or data: URI (AI-generated / uploaded)
  alt: string;
  credit?: string;
}

const PEXELS_ENDPOINT = "https://api.pexels.com/v1/search";

interface PexelsPhoto {
  src: { large2x: string; large: string };
  alt: string | null;
  photographer: string;
}

async function searchPexels(query: string): Promise<PexelsPhoto | null> {
  const key = process.env.PEXELS_API_KEY;
  if (!key) return null;
  try {
    const url = `${PEXELS_ENDPOINT}?query=${encodeURIComponent(query)}&per_page=1&orientation=landscape`;
    const res = await fetch(url, { headers: { Authorization: key } });
    if (!res.ok) return null;
    const data = (await res.json()) as { photos: PexelsPhoto[] };
    return data.photos?.[0] ?? null;
  } catch {
    return null;
  }
}

/** Mirrors the original CLI tool's AI photo generation: OpenRouter's
 * image-modality response returns the picture as a base64 data URL on
 * message.images[0], which isn't in the openai SDK's TS types — this reads
 * the same shape that tool's working code already relies on. */
async function generateAiImage(prompt: string): Promise<string | null> {
  try {
    // Same key, same rate limit as the text calls — so same queue.
    const response = await openrouterQueue.run(() =>
      openrouter.chat.completions.create({
        model: IMAGE_MODEL,
        messages: [
          {
            role: "user",
            content: `Generate a high-quality, photorealistic marketing photo for a website. ${prompt}. No text or watermarks in the image.`,
          },
        ],
        // @ts-expect-error OpenRouter-specific field, not in the openai SDK's types
        modalities: ["image", "text"],
      })
    );
    const message = firstChoiceOrThrow<{ images?: Array<{ image_url?: { url?: string } }> }>(
      response,
      `AI image generation (${IMAGE_MODEL})`
    );
    const url = message.images?.[0]?.image_url?.url;
    return url ?? null;
  } catch (err) {
    // Image sourcing degrades gracefully (falls back to a styled panel) —
    // log so it's diagnosable, but never throw out of this function.
    console.error("generateAiImage failed:", err instanceof Error ? err.message : err);
    return null;
  }
}

/** Sentinel used when no real image could be sourced. Prompt builders
 * render this as a styled gradient panel, never a broken <img>. */
export const PANEL_SENTINEL = "__PANEL__";

export function isRealImage(src: string): boolean {
  return src !== PANEL_SENTINEL;
}

/**
 * Prompts must never carry raw base64 image bytes as text. A single
 * multi-MB uploaded/AI photo can be hundreds of thousands to millions of
 * tokens once base64-encoded and tokenized — and every place that re-embeds
 * the same src (the image catalog, the chosen mockup HTML reused across the
 * plan prompt and every page prompt) multiplies that cost. An ImageRegistry
 * swaps every `data:` URI for a short `__IMG_REF_n__` token before it
 * touches a prompt, and swaps it back on the model's output afterward — the
 * model only ever sees/echoes the cheap token, never the bytes.
 */
export interface ImageRegistry {
  /** Replaces every `data:...;base64,...` URI in `text` with a short
   * placeholder token (reused if the same src appears again). Safe to call
   * on a single bare src or a full HTML blob; a no-op on https URLs, the
   * panel sentinel, or text that's already been compressed. */
  compress(text: string): string;
  /** Swaps every placeholder token in `text` back to the real `data:` URI
   * it stands for. Call once on the model's raw output, before any further
   * postprocessing. */
  resolve(text: string): string;
}

const DATA_URI_RE = /data:[\w/.+-]+;base64,[A-Za-z0-9+/=]+/g;

export function createImageRegistry(): ImageRegistry {
  const srcToToken = new Map<string, string>();
  const tokenToSrc = new Map<string, string>();
  let counter = 0;

  return {
    compress(text: string): string {
      if (!text) return text;
      return text.replace(DATA_URI_RE, (match) => {
        let token = srcToToken.get(match);
        if (!token) {
          counter += 1;
          token = `__IMG_REF_${counter}__`;
          srcToToken.set(match, token);
          tokenToSrc.set(token, match);
        }
        return token;
      });
    },
    resolve(text: string): string {
      if (!text) return text;
      let out = text;
      for (const [token, src] of tokenToSrc) {
        out = out.split(token).join(src);
      }
      return out;
    },
  };
}

/**
 * Resolves one page's worth of image specs (from the plan) into real
 * sources, according to the person's chosen imageSource. Always returns one
 * entry per spec, falling back to a styled panel rather than ever leaving a
 * dead/missing image.
 */
export async function sourceImagesForPage(
  specs: PlannedPageImage[],
  opts: {
    imageSource: DesignPrefs["imageSource"];
    industry: string;
    companyName: string;
    uploaded: ExtractedImage[];
    /** running offset into `uploaded` so different pages get different
     * client photos instead of all reusing photo #1 */
    uploadedOffset: number;
  }
): Promise<SourcedImage[]> {
  const results: SourcedImage[] = [];

  for (let i = 0; i < specs.length; i++) {
    const spec = specs[i];
    let src: string = PANEL_SENTINEL;
    let credit: string | undefined;

    if (opts.imageSource === "uploaded" && opts.uploaded.length > 0) {
      const img = opts.uploaded[(opts.uploadedOffset + i) % opts.uploaded.length];
      src = img.dataUrl;
    } else if (opts.imageSource === "ai") {
      const generated = await generateAiImage(
        `${spec.desc}. Business: ${opts.companyName}, a ${opts.industry} business.`
      );
      if (generated) src = generated;
    } else if (opts.imageSource === "pexels") {
      const photo = await searchPexels(`${spec.desc} ${opts.industry}`);
      if (photo) {
        src = photo.src.large2x;
        credit = photo.photographer;
      }
    }
    // "placeholder" source, or any failed lookup above, keeps the sentinel.

    results.push({ section: spec.section, desc: spec.desc, src, alt: spec.desc, credit });
  }

  return results;
}

/** Renders a page's resolved images into the instruction block page-build
 * prompts read, matching the original tool's "USE THESE IMAGES" catalog
 * format that kept image placement predictable. */
export function renderImageCatalog(images: SourcedImage[], registry?: ImageRegistry): string {
  if (images.length === 0) {
    return "No images assigned to this page — use styled color/gradient panels or icon compositions instead, per the design system.";
  }
  const lines = images.map((img) => {
    if (img.src === PANEL_SENTINEL) {
      return `- "${img.section}" section: NO image available — render a styled gradient/color panel here (${img.desc}), never a broken <img> tag or an external URL.`;
    }
    const src = registry ? registry.compress(img.src) : img.src;
    return `- "${img.section}" section: use exactly this image src="${src}" alt="${img.alt}" (${img.desc})`;
  });
  return (
    "IMAGES FOR THIS PAGE — use each EXACTLY ONCE, in its named section, using the exact src given. " +
    "Never reuse the same src twice on one page, never invent a different external image URL:\n" +
    lines.join("\n")
  );
}
