import os, re, time, json, base64, pathlib, webbrowser, requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
MODEL = "anthropic/claude-sonnet-4.6"        # main model: plan + page builds
CHEAP_MODEL = "anthropic/claude-sonnet-4.6"  # utility model: labeling, extraction
PREVIEW_MODEL = "anthropic/claude-opus-4.8"  # design previews (higher quality)
CALLS = {"main": 0, "cheap": 0, "image": 0}  # cost tracker
IMAGE_MODEL = "google/gemini-2.5-flash-image"  # affordable image generation (~$0.04/image)
N_PREVIEWS = 3  # how many design previews the customer chooses from

import datetime
# Each run saves into its OWN folder (named after the company) so nothing is overwritten.
RUN_STAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
SITE_DIR = None  # set once we know the company name (after the questions)


# ============================================================
#  DESIGN SYSTEM KIT  (enforced on every generation)
# ============================================================
DESIGN_SYSTEM = """
DESIGN KNOWLEDGE PACK — follow all of this on every page. The goal is a site that looks
intentionally designed by a professional, never like a generic AI template.

TYPOGRAPHY
- Use a characterful display font for headings + a clean body font (from the chosen mockup). Never default fonts.
- Clear scale: hero headline very large (clamp(2.5rem, 6vw, 4.5rem)), section headings ~2rem, body 1rem-1.125rem.
- Line-height: tight on headlines (1.1), comfortable on body (1.6). Max text width ~65ch for paragraphs.
- Small uppercase "eyebrow" labels (letter-spacing .1em, small size, accent color) above section headings.

COLOR — 60/30/10 RULE
- ~60% neutral background, ~30% secondary surfaces, ~10% accent. Accent ONLY on CTAs, eyebrows, key highlights.
- Never use the accent for large areas or body text. Ensure WCAG AA contrast everywhere.
- Use tonal variations of the palette for section backgrounds to create rhythm (alternate light/subtle-tint sections).

LAYOUT & COMPOSITION
- Vary section layouts across the page — never stack identical centered blocks. Rotate between:
  split image/text (alternating sides), 3-card grid, full-width statement band, bento-style mixed grid,
  stat strip, testimonial spotlight. Adjacent sections must use DIFFERENT layouts.
- Generous vertical rhythm: py-20/py-24 between sections; consistent max-w-6xl/7xl container.
- Use asymmetry deliberately (offset images, overlapping cards, staggered grids) for visual interest.
- Every section: eyebrow label -> heading -> one line of supporting text -> content.

COMPONENTS
- Buttons: one solid primary (accent bg), one ghost/outline secondary. px-6 py-3, font-medium,
  rounded-lg/xl, smooth 200ms transitions, visible hover (slight lift/darken) and focus-visible ring.
- Cards: consistent anatomy (image -> title -> body -> action), equal heights in grids, rounded-xl,
  soft layered shadows (shadow-sm rest, shadow-lg hover with -translate-y-1).
- Nav: sticky, subtle backdrop blur, active link clearly marked, mobile hamburger that actually works.
- Forms: clear labels, roomy inputs (px-4 py-3), visible focus states, inline validation, a real success state.

IMAGERY
- Images get rounded corners (rounded-xl/2xl) and purposeful sizing — never tiny thumbnails in huge sections.
- If a section has no assigned image, use a styled gradient/color panel or an icon composition — NEVER repeat
  another section's image and never use external image URLs.

WHAT MAKES IT LOOK CHEAP (avoid all of these)
- Identical centered text blocks stacked repeatedly; every section the same width and alignment.
- Accent color splashed everywhere; pure black on pure white; default system fonts.
- Dead links, placeholder lorem ipsum, empty sections, buttons that do nothing.
- Overcrowding: too many words per section. Be concise and confident, real copy for THIS brand.

QUALITY BASELINE
- Semantic HTML5 (header/main/section/footer), alt text on every image, keyboard-visible focus.
- ANIMATION: use the AOS library (https://unpkg.com/aos@2.3.1/dist/aos.css and aos.js, init AOS.init()).
  Tasteful scroll reveals (fade-up, staggered delays), smooth hover transitions. Match the chosen animation
  level. Wrap motion in prefers-reduced-motion so it disables cleanly.
- Mobile-first responsive; test mentally at 375px, 768px, 1280px. Nothing overflows or breaks.
"""

# ============================================================
#  SECTION PATTERN LIBRARY + ICONS + QUALITY REFERENCE
#  (appended to DESIGN_SYSTEM — raises output quality, still single-file)
# ============================================================
SECTION_PATTERNS = """
SECTION PATTERN LIBRARY — when building a section, pick a fitting pattern and adapt it to the brand.
Rotate patterns so adjacent sections never look the same. All patterns are Tailwind, single-file safe.

HERO (choose one):
- Split hero: left column = eyebrow + big headline + subline + two buttons; right column = image in a
  rounded-2xl frame with a soft shadow and a small floating stat/badge card overlapping a corner.
- Centered hero: centered eyebrow + oversized headline (clamp) + subline + buttons, full-bleed background
  image with a dark gradient overlay, a thin scroll cue at the bottom.
- Bento hero: headline block + a small asymmetric grid of 3-4 rounded tiles (image, stat, quote, logo).

FEATURES / SERVICES:
- 3-col icon cards: each card = icon in a rounded tinted square, title, 2-line description, subtle hover lift.
- Alternating rows: image left / text right, then flip — each row one feature, generous spacing.
- Bento grid: mixed-size rounded cards, one large "hero feature" tile + smaller supporting tiles.

PRICING:
- 3 tier cards, the middle one elevated (accent border, "Most Popular" badge, slightly scaled up),
  each with price, per-unit label, checked feature list (icon bullets), and a CTA button.

TESTIMONIALS:
- Quote spotlight: one large centered quote + avatar + name/role, with small nav dots.
- 3-card grid: each card = quote, avatar row (name + role), subtle star row.

STATS STRIP: a thin band (tinted or dark) with 3-4 big numbers + labels, evenly spaced.

TEAM: rounded portrait cards in a grid, name + role + small social icons on hover.

GALLERY: masonry or uniform rounded grid with hover zoom + optional lightbox.

CONTACT: two columns — left = form (labeled inputs, roomy, validation, success state);
right = location card with address, hours, and a map-placeholder block.

FOOTER: multi-column (brand + short line, quick links, contact, socials) over a tinted/dark band,
thin divider, small legal row.
"""

ICON_RULE = """
ICONS: load Lucide icons via CDN (<script src="https://unpkg.com/lucide@latest"></script> and call
lucide.createIcons()). Use <i data-lucide="icon-name"></i> for feature cards, list bullets, contact
details, and social links. Never use emoji as icons. Keep icon sizing consistent (e.g. w-6 h-6).
"""

QUALITY_REFERENCE = """
QUALITY BAR — the output should feel like a hand-crafted studio site: confident whitespace, a clear
visual hierarchy, one strong accent used sparingly, consistent rounded corners and soft shadows,
real specific copy (never lorem ipsum), and at least one moment of visual interest per section
(an overlap, a badge, an asymmetric layout, a subtle gradient). If a section looks like a plain
centered text block, redesign it using a pattern from the library above.
"""

DESIGN_SYSTEM = DESIGN_SYSTEM + SECTION_PATTERNS + ICON_RULE + QUALITY_REFERENCE

# Real-world section blueprints mined from HyperUI (MIT-licensed, HTML/Tailwind).
# Loaded into a dict so each page only gets the blueprints its sections need (keeps prompts lean),
# and a RANDOM variant is chosen each run so two similar companies don't get identical layouts.
import random
BLUEPRINTS = {}   # {"PRICING TIERS": [code, code], ...}
try:
    _ref = pathlib.Path(__file__).with_name("hyperui_reference.txt")
    if _ref.exists():
        _txt = _ref.read_text(encoding="utf-8")
        for _chunk in _txt.split("### ")[1:]:
            _head, _, _code = _chunk.partition("\n")
            _key = re.sub(r"\s*\((?:variant|tailblocks)\s*\d+\)\s*$", "", _head).strip().upper()
            BLUEPRINTS.setdefault(_key, []).append(_code.strip())
        print(f"  design blueprints loaded ({sum(len(v) for v in BLUEPRINTS.values())} patterns, "
              f"{len(BLUEPRINTS)} types)")
except Exception:
    pass

# map a page's section name -> blueprint type
SECTION_MAP = [
    (r"hero|banner|intro|welcome|masthead",             "HERO / SPLIT SECTION"),
    (r"pricing|plan|membership|package|tier|rate",      "PRICING TIERS"),
    (r"feature|service|what we|offer|program|capabilit","FEATURE GRID"),
    (r"testimonial|review|quote|client say|what.*say",  "TESTIMONIALS"),
    (r"team|coach|staff|people|founder|leadership|chef","TEAM"),
    (r"stat|number|impact|metric|result|achievement",   "STATS STRIP"),
    (r"process|step|how it works|timeline|journey|milestone|our story|history", "PROCESS STEPS / TIMELINE"),
    (r"faq|question|frequently",                        "FAQ"),
    (r"contact|form|map|location|book|reserve|visit|enquir|appointment", "CONTACT + FORM"),
    (r"gallery|portfolio|showcase|work|project|case stud", "MEDIA / GALLERY"),
    (r"blog|news|article|post|insight|resource",        "BLOG / ARTICLE CARDS"),
    (r"newsletter|subscribe|signup|mailing",            "NEWSLETTER SIGNUP"),
    (r"logo|client|partner|brand|trusted|certif",       "LOGO CLOUD"),
    (r"product|shop|menu|item|collection|catalog",      "PRODUCT CARD"),
    (r"compar|versus|vs\b|table",                       "COMPARISON TABLE"),
    (r"cta|call to action|get started|join|sign up",    "CTA BAND"),
    (r"about|story|mission|vision|value|philosophy|who we are", "CONTENT SECTION"),
    (r"card|grid|highlight",                            "CARD GRID"),
    (r"accordion|expand|collaps",                       "ACCORDION"),
    (r"award|recognition|press",                        "STAT CARDS"),
]

def blueprints_for(sections):
    """Return blueprint snippets relevant to THIS page's sections (random variant each time)."""
    wanted, out = [], []
    for s in sections:
        low = s.lower()
        for pat, key in SECTION_MAP:
            if re.search(pat, low) and key in BLUEPRINTS and key not in wanted:
                wanted.append(key); break
    # always give the shell patterns
    for key in ("NAV HEADER", "FOOTER"):
        if key in BLUEPRINTS and key not in wanted:
            wanted.append(key)
    for key in wanted:
        out.append(f"### {key}\n{random.choice(BLUEPRINTS[key])}")
    if not out:
        return ""
    return ("\n\nREAL SECTION BLUEPRINTS — imitate these proven HTML/Tailwind structures for this page's "
            "sections, but rewrite all copy for THIS brand, apply the chosen palette/fonts, and use the "
            "assigned images (never the placeholder Unsplash URLs):\n" + "\n\n".join(out))

# ============================================================
#  INDUSTRY STYLE PRESETS  (auto-picked from the intake answers)
# ============================================================
INDUSTRY_PRESETS = {
    # food & hospitality
    "bakery":     "Warm Parisian patisserie feel: cream, gold, espresso tones, elegant serifs, soft light imagery, indulgent copy. Menu grids with prices, 'order' CTAs.",
    "food":       "Warm, appetizing, artisanal. Close-up textures, warm tones, serif elegance. Menu-style product grids with prices.",
    "restaurant": "Appetite-driven: rich food photography, warm palette, menu sections with prices, reservation CTAs, chef/story highlight.",
    "cafe":       "Cozy and inviting: warm neutrals, casual serif/sans mix, menu boards, location & hours prominent, community feel.",
    "catering":   "Elegant abundance: spread/platter imagery, event-focused sections, package tiers, enquiry CTAs.",
    "hotel":      "Serene luxury: full-width imagery, airy spacing, room/amenity cards, booking CTAs, location highlights.",
    "travel":     "Aspirational: immersive full-width imagery, light airy type, destination cards, itinerary highlights, 'book now' CTAs.",
    # professional services
    "law":        "Restrained authority: serif headings, navy/charcoal palette, generous whitespace, credential and results sections, trust signals.",
    "consulting": "Professional clarity: structured grids, muted palette with one strong accent, case-study cards, process timelines, outcome metrics.",
    "accounting": "Precise and trustworthy: clean grids, navy/green tones, service cards, compliance badges, consultation CTAs.",
    "finance":    "Confident stability: deep blues, structured layout, metric stat strips, service tiers, regulatory trust signals.",
    "insurance":  "Reassuring clarity: calm palette, plan-comparison cards, claim-process steps, quote CTAs.",
    "marketing":  "Bold creativity: vivid accent colors, striking type, portfolio grid, results metrics, punchy copy.",
    "agency":     "Portfolio-forward: large case-study imagery, confident typography, client logos strip, project inquiry CTAs.",
    "recruitment":"People-focused: friendly photography, role/category cards, process steps, employer & candidate dual CTAs.",
    # health & personal care
    "health":     "Calm and trustworthy: soft blues/greens, airy spacing, rounded shapes, friendly photography, clear service cards, appointment CTAs.",
    "clinic":     "Clean medical trust: white space, soft blue accents, doctor/team cards, services grid, easy booking.",
    "dental":     "Bright and reassuring: white/teal palette, smile photography, treatment cards, before/after, booking CTAs.",
    "pharmacy":   "Clean and accessible: green/white tones, product categories, health-tip sections, location & hours prominent.",
    "fitness":    "Energetic: bold condensed headlines, high-contrast dark sections, action photography, program cards, transformation stats.",
    "beauty":     "Elegant and sensory: soft pastels or rich jewel tones, refined serifs, editorial imagery, treatment menus, booking CTAs.",
    "salon":      "Chic and personal: fashion-style imagery, elegant type, service menu with prices, stylist team, booking CTAs.",
    "spa":        "Tranquil luxury: muted naturals, airy whitespace, ritual/treatment cards, serene imagery, reservation CTAs.",
    # property & construction
    "real estate":"Premium and spacious: large property imagery, clean sans type, dark-on-light luxury feel, listing cards, location highlights.",
    "construction":"Solid and capable: strong slab typography, steel/earth tones, project portfolio grid, capability stats, tender/enquiry CTAs.",
    "architecture":"Minimal gallery feel: large project photography, restrained type, grid portfolio, studio philosophy section.",
    "interior":   "Editorial elegance: room photography, refined serif/sans pairing, portfolio grid, design-process steps, consultation CTAs.",
    "cleaning":   "Fresh and dependable: bright palette, before/after visuals, service packages with pricing, booking CTAs.",
    # trade, retail & industry
    "retail":     "Product-forward: clean grids, generous product imagery, clear pricing, promo bands, cart-style CTAs.",
    "trading":    "Global and capable: professional palette, product-category grid, logistics/partners strip, enquiry CTAs.",
    "logistics":  "Motion and reliability: bold type, route/fleet imagery, service cards, coverage map mention, tracking/quote CTAs.",
    "manufacturing":"Industrial strength: dark accents, machinery/facility imagery, capability specs, certifications strip, RFQ CTAs.",
    "automotive": "Sleek and technical: dark palette with metallic accents, vehicle photography, service cards, booking/quote CTAs.",
    "jewelry":    "Refined luxury: dark or cream backdrop, macro product photography, serif elegance, collection grids.",
    "furniture":  "Warm modern living: lifestyle room imagery, natural tones, collection grids, material/craft story.",
    # tech & creative
    "tech":       "Confident and modern: bold sans headlines, dark or high-contrast sections, gradient accents, product mockups, feature grids, stat strips.",
    "software":   "Product-led: clean UI screenshots, feature grids with icons, pricing tiers, integration logos, trial CTAs.",
    "photography":"Image-first: near-fullscreen gallery, minimal type, dark or white gallery backdrop, package tiers, booking CTAs.",
    "events":     "Celebratory energy: vibrant imagery, showcase gallery, service packages, testimonial spotlights, enquiry CTAs.",
    "education":  "Approachable and structured: friendly type, clear program cards, outcome stats, testimonial spotlights, enrollment CTAs.",
    "pets":       "Playful warmth: friendly rounded type, joyful animal photography, service cards, booking CTAs.",
}

def industry_style():
    """Ask the model to write a style direction tailored to THIS business (any industry).
    Falls back to the keyword dictionary if the call fails."""
    try:
        raw = chat(
            f"You are a web design director. In 3-4 short lines, give a visual style direction for a "
            f"marketing website for this business:\n"
            f"Business: {answers['industry']}\nCompany: {answers['company']}\nNotes: {answers['extra']}\n"
            f"Cover: mood, color tendencies, typography feel, imagery style, and 1-2 industry-specific "
            f"sections worth including (e.g. menu grid, case studies, booking). Be specific to this "
            f"industry, not generic. Plain text only, no markdown.",
            max_tokens=220, model=CHEAP_MODEL)
        direction = raw.strip()
        if direction:
            return f"INDUSTRY STYLE DIRECTION (tailored): {direction}"
    except Exception:
        pass
    text = f"{answers['industry']} {answers['extra']}".lower()
    for key, style in INDUSTRY_PRESETS.items():
        if key in text:
            return f"INDUSTRY STYLE DIRECTION ({key}): {style}"
    return ""

# ============================================================
#  FILE READING (for company profile upload)
# ============================================================
def read_profile_file(path):
    path = path.strip().strip('"').strip("'")
    p = pathlib.Path(path)
    if not p.exists():
        print("  File not found:", p); return None
    ext = p.suffix.lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
        if ext == ".docx":
            import docx
            return "\n".join(par.text for par in docx.Document(str(p)).paragraphs)
        if ext in (".txt", ".md"):
            return p.read_text(encoding="utf-8", errors="ignore")
        print("  Unsupported file type:", ext, "(use PDF, DOCX, or TXT)"); return None
    except ModuleNotFoundError as e:
        print(f"  Missing library to read {ext}: {e.name}. Run:  pip install pypdf python-docx")
        return None
    except Exception as e:
        print("  Could not read file:", e); return None

def extract_brief_from_text(text):
    prompt = f"""From this company profile / portfolio text, extract details for a website brief.
Return ONLY valid JSON with these keys (use "" if unknown):
{{"company":"","industry":"","audience":"","tagline":"","cta":"","extra":"(any products, services, tone, or must-haves worth noting)"}}

PROFILE TEXT:
{text[:8000]}"""
    raw = chat(prompt, max_tokens=800, model=CHEAP_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip()); raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        return {}


# ============================================================
#  IMAGE HELPERS  (customer photos  +  AI-generated images)
# ============================================================
def assets_dir():
    return SITE_DIR / "assets"

def extract_images_from_file(path):
    """Pull embedded images out of a PDF or DOCX into site/assets/. Returns list of saved paths."""
    path = path.strip().strip('"').strip("'")
    p = pathlib.Path(path)
    assets_dir().mkdir(parents=True, exist_ok=True)
    saved = []
    ext = p.suffix.lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            n = 0
            for page in reader.pages:
                for img in getattr(page, "images", []):
                    n += 1
                    fp = assets_dir() / f"client_{n}{pathlib.Path(img.name).suffix or '.png'}"
                    fp.write_bytes(img.data); saved.append(fp)
        elif ext == ".docx":
            import zipfile
            with zipfile.ZipFile(str(p)) as z:
                media = [m for m in z.namelist() if m.startswith("word/media/")]
                for i, m in enumerate(media, 1):
                    fp = assets_dir() / f"client_{i}{pathlib.Path(m).suffix}"
                    fp.write_bytes(z.read(m)); saved.append(fp)
    except Exception as e:
        print("  Couldn't extract images:", e)
    return saved

def label_image(fp):
    """Use Sonnet vision to describe one image so we place it well."""
    try:
        data = base64.b64encode(fp.read_bytes()).decode()
        ext = fp.suffix.lstrip(".").lower().replace("jpg", "jpeg") or "png"
        CALLS["cheap"] += 1
        r = client.chat.completions.create(
            model=CHEAP_MODEL, max_tokens=120,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "In 5 words or fewer, what is this image? (e.g. 'company logo', 'product photo - cake', 'team portrait', 'storefront'). Just the label."},
                {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{data}"}},
            ]}],
        )
        return r.choices[0].message.content.strip().strip(".")
    except Exception as e:
        return "image"

def generate_all_page_images(plan_obj, slugs):
    """Generate every page's images (from the plan's per-section specs) IN PARALLEL.
    Returns {page_name: catalog_string}. Zero extra text calls — descriptions come from the plan."""
    import concurrent.futures
    jobs = []
    for pg in plan_obj["pages"]:
        safe = slugs[pg["name"]]
        for k, spec in enumerate((pg.get("images") or [])[:2], 1):
            desc = spec.get("desc") or f"{answers['industry']} photo"
            sec = spec.get("section") or "page"
            jobs.append((pg["name"], sec, desc, f"{safe}_{k}.png"))
    results = {}
    if not jobs:
        return results
    print(f"\n  Generating {len(jobs)} images in parallel with {IMAGE_MODEL}...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(generate_image, d, fn): (page, sec, d, fn) for page, sec, d, fn in jobs}
        for f in concurrent.futures.as_completed(futs):
            page, sec, d, fn = futs[f]
            rel = f.result()
            if rel:
                print(f"    {rel}  ({page} / {sec})")
                results.setdefault(page, []).append((rel, sec, d))
    catalogs = {}
    for page, items in results.items():
        lines = "\n".join(f'- "{r}" -> use in the "{s}" section ({d})' for r, s, d in items)
        catalogs[page] = ("USE THESE IMAGES, EACH IN ITS NAMED SECTION (exact relative paths, unique to this page; "
                          "USE EACH IMAGE EXACTLY ONCE. Any section without an assigned image gets a styled color/gradient block — NEVER repeat an image on the page):\n" + lines)
    return catalogs

def generate_image(description, filename):
    """Generate one photo with an AI image model and save it into assets/. Returns relative path or None."""
    try:
        CALLS["image"] += 1
        r = client.chat.completions.create(
            model=IMAGE_MODEL,
            messages=[{"role": "user", "content":
                f"Generate a high-quality, photorealistic marketing photo for a website. {description}. "
                f"No text or watermarks in the image."}],
            extra_body={"modalities": ["image", "text"]},
        )
        msg = r.choices[0].message
        # OpenRouter returns generated images in message.images[].image_url.url as data URLs
        images = getattr(msg, "images", None)
        if not images and hasattr(msg, "model_dump"):
            images = msg.model_dump().get("images")
        if not images:
            return None
        first = images[0]
        if not isinstance(first, dict) and hasattr(first, "model_dump"):
            first = first.model_dump()
        url = first["image_url"]["url"] if isinstance(first["image_url"], dict) else first["image_url"].url
        b64 = url.split(",", 1)[1]
        assets_dir().mkdir(parents=True, exist_ok=True)
        fp = assets_dir() / filename
        fp.write_bytes(base64.b64decode(b64))
        return f"assets/{filename}"
    except Exception as e:
        print("    image-gen error:", e)
        return None

# ============================================================
#  STEP 1 — INTAKE QUESTIONS
# ============================================================
def ask_text(q):
    return input(f"\n{q}\n> ").strip() or "(not specified)"

def ask_choice(q, options):
    print(f"\n{q}")
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    while True:
        raw = input("> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Pick a number from the list.")

print("=" * 60)
print("  AI WEBSITE GENERATOR")
print("=" * 60)

def clean_html(t):
    t = re.sub(r"^```(?:html)?\s*", "", t.strip())
    return re.sub(r"\s*```$", "", t)

def chat(prompt, max_tokens=4000, model=None):
    m = model or MODEL
    CALLS["main" if m == MODEL else "cheap"] += 1
    r = client.chat.completions.create(
        model=m, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content

def review(label, value):
    """Show an auto-filled value; Enter keeps it, typing replaces it."""
    value = value or ""
    shown = value if value else "(empty)"
    new = input(f"\n{label}\n   current: {shown}\n   press Enter to keep, or type a new value:\n> ").strip()
    return new if new else (value or "(not specified)")

# ============================================================
#  INPUT: answers.json (from the intake web page) OR terminal
# ============================================================
FROM_JSON = pathlib.Path(__file__).with_name("answers.json")
answers = {}
catalog_from_json = None
if FROM_JSON.exists():
    print("Loading answers.json (from the intake page)...")
    _j = json.loads(FROM_JSON.read_text(encoding="utf-8"))
    for k in ("company","industry","audience","tagline","cta","extra",
              "style","palette","fonts","theme","animation"):
        answers[k] = _j.get(k) or "(not specified)"
    catalog_from_json = _j.get("pages") or []
    print(f"  loaded brand: {answers['company']}  ({len(catalog_from_json)} pages)")

if not answers:  # ---- terminal intake (only when no answers.json) ----
    # --- optional: upload a company profile to auto-fill ---
    prefill = {}
    profile_path = None   # remember the uploaded file so we can pull images from it later
    mode = ask_choice("How do you want to provide company info?",
        ["Upload a company profile file (PDF / Word / TXT)", "Answer the questions manually"])
    if mode.startswith("Upload"):
        raw_text = None
        while raw_text is None:
            path = input("\nDrag the file here or paste its full path (or type 'skip'):\n> ").strip()
            if path.lower() == "skip":
                break
            raw_text = read_profile_file(path)
            if raw_text is not None:
                profile_path = path
        if raw_text:
            print("\nReading the profile and extracting details...")
            prefill = extract_brief_from_text(raw_text)
            print("Done — review the auto-filled answers below.")

    answers = {}
    if prefill:
        answers["company"]  = review("1) Company / brand name?", prefill.get("company"))
        answers["industry"] = review("2) What does the company do?", prefill.get("industry"))
        answers["audience"] = review("3) Customers / target audience?", prefill.get("audience"))
        answers["tagline"]  = review("4) Tagline or main hero message?", prefill.get("tagline"))
    else:
        answers["company"]  = ask_text("1) Company / brand name?")
        answers["industry"] = ask_text("2) What does the company do? (one line)")
        answers["audience"] = ask_text("3) Who are the customers / target audience?")
        answers["tagline"]  = ask_text("4) A tagline or main hero message? (or leave blank)")

    # style / color / font / animation are always chosen (look & feel, not in a profile)
    answers["style"]     = ask_choice("5) Overall visual style?",
        ["Luxury / elegant", "Modern / minimal", "Bold / playful",
         "Corporate / professional", "Warm / organic", "Dark / premium tech",
         "Let the AI choose based on the company's field"])
    PALETTES = [
        ("Modern Blue",    {"primary": "#2563EB", "secondary": "#60A5FA", "background": "#F8FAFC", "text": "#0F172A"}),
        ("Nature Green",   {"primary": "#16A34A", "secondary": "#86EFAC", "background": "#ECFDF5", "text": "#14532D"}),
        ("Elegant Purple", {"primary": "#7C3AED", "secondary": "#C4B5FD", "background": "#FAF5FF", "text": "#312E81"}),
        ("Warm Orange",    {"primary": "#EA580C", "secondary": "#FDBA74", "background": "#FFF7ED", "text": "#7C2D12"}),
        ("Minimal",        {"primary": "#111827", "secondary": "#64748B", "background": "#FFFFFF", "text": "#1E293B"}),
        ("Luxury Gold",    {"primary": "#D4AF37", "secondary": "#EFD687", "background": "#141414", "text": "#F7F7F7"}),
        ("Soft Pink",      {"primary": "#EC4899", "secondary": "#F9A8D4", "background": "#FDF2F8", "text": "#831843"}),
    ]

    def palette_text(roles):
        return (f"Primary {roles['primary']}, Secondary {roles['secondary']}, "
                f"Background {roles['background']}, Text {roles['text']} "
                f"(use these exact hex colors in these exact roles)")

    print("\n6) Color palette?")
    for i, (nm, roles) in enumerate(PALETTES, 1):
        print(f"  {i}. {nm:15} {roles['primary']}  {roles['secondary']}  {roles['background']}  {roles['text']}")
    print(f"  {len(PALETTES)+1}. Custom — enter my own colors")
    print(f"  {len(PALETTES)+2}. Let the AI choose to fit the brand")
    while True:
        _p = input("> ").strip()
        if _p.isdigit() and 1 <= int(_p) <= len(PALETTES) + 2: break
        print("  Pick a number from the list.")
    _p = int(_p)
    if _p <= len(PALETTES):
        nm, roles = PALETTES[_p - 1]
        answers["palette"] = f"{nm}: " + palette_text(roles)
    elif _p == len(PALETTES) + 1:
        DIM = "\033[90m"; RST = "\033[0m"; CYAN = "\033[96m"
        def ask_hex(label, required=True):
            while True:
                raw_c = input(f"  {label} > ").strip()
                if not raw_c and not required:
                    return None
                if re.fullmatch(r"#?[0-9a-fA-F]{6}", raw_c):
                    return raw_c if raw_c.startswith("#") else "#" + raw_c
                print("    Enter a valid 6-digit hex like #2563EB")
        print("\nCustom Palette")
        # checkbox-style toggle
        tog = input(f"  [ ] Enter more specific colors   (press Enter to skip, or type 'x' to enable) > ").strip().lower()
        more = tog in ("x", "y", "yes", "1", "[x]")
        box = "[x]" if more else "[ ]"
        print(f"  {box} Enter more specific colors\n")

        prim = ask_hex("PRIMARY    (e.g. #2563EB)")
        if more:
            seco = ask_hex("SECONDARY  (e.g. #60A5FA)")
            bg   = ask_hex("BACKGROUND (e.g. #F8FAFC)")
            txt  = ask_hex("TEXT       (e.g. #0F172A)")
            answers["palette"] = (f"Custom palette (use these exact hex colors in these roles): "
                                  f"Primary {prim}, Secondary {seco}, Background {bg}, Text {txt}")
        else:
            # show the disabled fields greyed out, like the modal
            print(f"{DIM}  SECONDARY  (auto)  — AI will match{RST}")
            print(f"{DIM}  BACKGROUND (auto)  — AI will match{RST}")
            print(f"{DIM}  TEXT       (auto)  — AI will match{RST}")
            answers["palette"] = (f"Custom palette — use this EXACT primary color in its role: Primary {prim}. "
                                  f"Then generate a harmonious, accessible Secondary, Background, and Text color "
                                  f"derived from this primary (ensure strong text/background contrast, WCAG AA).")
    else:
        answers["palette"] = "Let the AI choose colors to fit the brand"

    FONT_PAIRS = [
        ("Modern Startup",    "Poppins",          "Inter"),
        ("Elegant Editorial", "Playfair Display", "Source Sans 3"),
        ("Corporate",         "Montserrat",       "Open Sans"),
        ("Professional Blog", "Merriweather",     "Lato"),
        ("Tech & SaaS",       "Space Grotesk",    "Inter"),
        ("Luxury Brand",      "DM Serif Display", "Manrope"),
        ("Creative Studio",   "Bebas Neue",       "Nunito Sans"),
    ]
    print("\n7) Font pairing (heading + body)?")
    for i, (nm, h, b) in enumerate(FONT_PAIRS, 1):
        print(f"  {i}. {nm:18} {h}  +  {b}")
    print(f"  {len(FONT_PAIRS)+1}. Custom — choose my own fonts")
    print(f"  {len(FONT_PAIRS)+2}. Let the AI choose")
    while True:
        _f = input("> ").strip()
        if _f.isdigit() and 1 <= int(_f) <= len(FONT_PAIRS) + 2: break
        print("  Pick a number from the list.")
    _f = int(_f)
    if _f <= len(FONT_PAIRS):
        nm, h, b = FONT_PAIRS[_f - 1]
        answers["fonts"] = f"Headings: {h}, Body: {b} (Google Fonts — use exactly these)"
    elif _f == len(FONT_PAIRS) + 1:
        print("\nCustom fonts — use Google Font names so they load correctly:")
        h = input("  HEADING font (e.g. Playfair Display) > ").strip() or "let the AI choose"
        b = input("  BODY font    (e.g. Inter)            > ").strip() or "let the AI choose"
        answers["fonts"] = (f"Headings: {h}, Body: {b} (load from Google Fonts; if a font isn't available "
                            f"there, use the closest Google Fonts equivalent)")
    else:
        answers["fonts"] = "Let the AI choose fonts to fit the brand"

    # Theme is always light + dark with a working toggle (no question asked)
    answers["theme"]     = "Light + dark (include a theme toggle)"

    answers["animation"] = ask_choice("8) Animation level?",
        ["Minimal (subtle & clean)", "Low (light movements)",
         "Balanced (recommended)", "High (more dynamic)"])

    if prefill:
        answers["cta"] = review("9) Main call-to-action?", prefill.get("cta"))
    else:
        answers["cta"] = ask_text("9) Main call-to-action? (e.g. 'Order Now', 'Book a Call')")

    # optional free-text extra info (always asked last)
    _pre_extra = prefill.get("extra") if prefill else ""
    if _pre_extra:
        print(f"\n10) Anything else? (optional)\n   from your profile: {_pre_extra[:200]}"
              f"{'...' if len(_pre_extra) > 200 else ''}")
        _more = input("   press Enter to keep, or add/replace with your own text:\n> ").strip()
        answers["extra"] = _more if _more else _pre_extra
    else:
        _more = input("\n10) Anything else you'd like to add? (optional — press Enter to skip)\n"
                      "   e.g. products, services, awards, opening hours, must-have sections\n> ").strip()
        answers["extra"] = _more if _more else "(not specified)"

brief = "\n".join(f"{k.upper()}: {v}" for k, v in answers.items())
_ind = industry_style()
if _ind:
    brief += "\n" + _ind
    print(f"  ({_ind.split(':')[0]} applied)")

# name the output folder after the company (+ a short timestamp so runs don't clash)
def folder_safe(name):
    import unicodedata
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    return s or "site"
SITE_DIR = pathlib.Path(f"{folder_safe(answers['company'])}_{RUN_STAMP}")


import unicodedata

def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "page"

# ============================================================
#  PAGE & SECTION BUILDER  (defaults provided — add or change anything, like the Figma)
# ============================================================
DEFAULT_PAGES = [
    {"name": "Home",      "selected": True,  "sections": ["Hero Section", "Features", "Testimonials", "Call To Action"]},
    {"name": "About Us",  "selected": True,  "sections": ["About Hero", "Our Story", "Team Members", "Values"]},
    {"name": "Services",  "selected": True,  "sections": ["Services Hero", "Service Cards", "Pricing", "FAQ"]},
    {"name": "Portfolio", "selected": True,  "sections": ["Portfolio Hero", "Gallery", "Case Studies"]},
    {"name": "Blog",      "selected": False, "sections": ["Blog Hero", "Blog Posts", "Newsletter"]},
    {"name": "Contact",   "selected": True,  "sections": ["Contact Hero", "Contact Form", "Map / Location"]},
]

def show_pages(cat):
    print("\n" + "=" * 60 + "\n  YOUR PAGES  (nav & footer are always included)\n" + "=" * 60)
    for i, p in enumerate(cat, 1):
        mark = "[x]" if p["selected"] else "[ ]"
        print(f"  {i}. {mark} {p['name']:12} — {', '.join(p['sections'])}")
    print("=" * 60)
    print("Commands:  t N (select/unselect) | r N NewName | s N (edit sections)")
    print("           a PageName (add page) | done")

def edit_sections(page):
    while True:
        print(f"\n  Sections of {page['name']}:")
        for j, s in enumerate(page["sections"], 1):
            print(f"    {j}. {s}")
        print("  Commands: a SectionName (add) | d N (delete) | r N NewName | done")
        cmd = input("  > ").strip()
        if cmd.lower() == "done":
            return
        if cmd.lower().startswith("a ") and len(cmd) > 2:
            page["sections"].append(cmd[2:].strip())
        elif cmd.lower().startswith("d ") and cmd[2:].strip().isdigit():
            k = int(cmd[2:].strip()) - 1
            if 0 <= k < len(page["sections"]): page["sections"].pop(k)
        elif cmd.lower().startswith("r ") and " " in cmd[2:].strip():
            num, new = cmd[2:].strip().split(" ", 1)
            if num.isdigit() and 0 <= int(num)-1 < len(page["sections"]):
                page["sections"][int(num)-1] = new.strip()
        else:
            print("  ?")

if catalog_from_json is not None:
    # pages came from the intake web page
    site_struct = {"pages": [{"name": p["name"], "is_home": False,
                              "sections": p.get("sections", [])} for p in catalog_from_json]}
    if not site_struct["pages"]:
        print("answers.json has no pages."); raise SystemExit
    site_struct["pages"][0]["is_home"] = True
    plan_obj = site_struct
else:
    catalog = [dict(p, sections=list(p["sections"])) for p in DEFAULT_PAGES]
    while True:
        show_pages(catalog)
        cmd = input("> ").strip()
        if cmd.lower() == "done":
            if any(p["selected"] for p in catalog): break
            print("Select at least one page."); continue
        if cmd.lower().startswith("t ") and cmd[2:].strip().isdigit():
            k = int(cmd[2:].strip()) - 1
            if 0 <= k < len(catalog): catalog[k]["selected"] = not catalog[k]["selected"]
        elif cmd.lower().startswith("r ") and " " in cmd[2:].strip():
            num, new = cmd[2:].strip().split(" ", 1)
            if num.isdigit() and 0 <= int(num)-1 < len(catalog):
                _pg = catalog[int(num)-1]
                _old, _new = _pg["name"].strip(), new.strip()
                _pg["name"] = _new
                # sections often embed the old page name ("Blog Hero", "Blog Posts") — update them too
                _pg["sections"] = [re.sub(re.escape(_old), _new, s, flags=re.I) for s in _pg["sections"]]
                print(f"  renamed to '{_new}' (sections updated)")
        elif cmd.lower().startswith("s ") and cmd[2:].strip().isdigit():
            k = int(cmd[2:].strip()) - 1
            if 0 <= k < len(catalog): edit_sections(catalog[k])
        elif cmd.lower().startswith("a ") and len(cmd) > 2:
            catalog.append({"name": cmd[2:].strip(), "selected": True,
                            "sections": ["Hero", "Content", "Call To Action"]})
        else:
            print("?")

    site_struct = {"pages": [{"name": p["name"], "is_home": False, "sections": p["sections"]}
                              for p in catalog if p["selected"]]}
    site_struct["pages"][0]["is_home"] = True   # first selected page is the homepage
    plan_obj = site_struct                       # downstream code reads plan_obj["pages"]

pages, slugs = [], {}
for pg in plan_obj["pages"]:
    name = pg["name"]
    pages.append(name)
    slug = "index" if pg.get("is_home") else slugify(name)
    base, k = slug, 2
    while slug in slugs.values():
        slug = f"{base}-{k}"; k += 1
    slugs[name] = slug
if "index" not in slugs.values():
    slugs[pages[0]] = "index"
print(f"\nBuilding {len(pages)} pages: " + ", ".join(pages))

# generate ONE shared, on-topic hero image up front; all 5 previews reuse this exact local file
# (real photo of the business, identical in thumbnail and full view, no flaky image hosts)
print("  creating a themed preview image for the mockups...")
SITE_DIR.mkdir(exist_ok=True)
PREVIEW_IMG = generate_image(
    f"A professional, appealing hero photo representing this business: {answers['industry']} "
    f"({answers['company']}). Bright, high-quality, marketing-style.",
    "preview_hero.png")
if PREVIEW_IMG:
    # copy it next to the mockups (same folder) and use a plain relative filename — most reliable
    import shutil as _sh
    _sh.copyfile(SITE_DIR / "assets" / "preview_hero.png", "preview_hero.png")
    PREVIEW_REL = "preview_hero.png"
    print(f"  preview image ready")
else:
    PREVIEW_REL = ""
    print("  (image-gen unavailable — previews will use styled gradient panels instead of a photo)")


# ============================================================
#  STEP 2 — DESIGN MOCKUPS (pick by look)
# ============================================================
print(f"\nGenerating {N_PREVIEWS} different website designs based on your answers...")
print("(one-screen mockups — this takes a minute)\n")

import concurrent.futures

# ---- HERO ARCHETYPES: 12 structurally different skeletons; 3 are drawn AT RANDOM each run ----
# Randomness lives in the STRUCTURE, so two companies in the same industry never get the same 3.
ARCHETYPES = [
    ("Split editorial", "LIGHT background. Two-column hero: left = eyebrow + big headline + subline + CTAs; "
     "right = hero image in a rounded frame. NO full-bleed dark photo. Whitespace-forward."),
    ("Bold color-block", "The palette's PRIMARY color as a large solid background block behind the hero text "
     "(not a photo). Oversized punchy headline in a contrasting color. Image is a small accent or omitted."),
    ("Modern overlay", "Full-width hero image with a tint of the primary color over it; headline on top, "
     "glassy/rounded CTA buttons. Sleek and contemporary."),
    ("Bento grid", "Headline block plus an asymmetric grid of 3-4 rounded tiles (image tile, stat tile, "
     "quote tile, CTA tile). Modular and modern."),
    ("Centered statement", "Centered eyebrow + oversized headline + subline + two CTAs on a clean tinted "
     "background. A thin strip of stats or logos beneath. No large photo."),
    ("Offset asymmetric", "Headline pushed left and overlapping a large image that bleeds off the right edge. "
     "A floating stat/badge card overlaps the image corner."),
    ("Magazine editorial", "Serif display headline, a thin rule line, two-column text intro, and a wide "
     "image band beneath. Print-inspired, refined."),
    ("Dark premium", "Deep dark background from the palette with glowing accent highlights, a luminous "
     "headline, and a subtle product/hero image with soft glow."),
    ("Sidebar hero", "A narrow vertical accent panel (primary color) on one side with the logo/eyebrow, "
     "and the headline + content occupying the wide remaining area."),
    ("Stacked layers", "Headline over a soft gradient background, with an image card floating below-center "
     "and overlapping the next section (depth via layering and shadow)."),
    ("Minimal type-first", "Almost no imagery: enormous typographic headline, tiny supporting line, one "
     "understated CTA, generous whitespace, one small accent detail."),
    ("Feature showcase", "Hero with a compact headline on the left and a mini feature/stat list on the right, "
     "plus a wide supporting image band below the fold line."),
]

def build_directions(n):
    """Draw n random archetypes, then have the AI tailor each to THIS brand.
    Random structure + brand-specific styling = different previews for every company."""
    picks = random.sample(ARCHETYPES, min(n, len(ARCHETYPES)))
    try:
        arche_txt = "\n".join(f"{i+1}. {nm}: {ds}" for i, (nm, ds) in enumerate(picks))
        raw = chat(
            f"You are an art director. For the business below, tailor each hero layout archetype into a "
            f"specific design direction for THIS brand (mood, color emphasis, type treatment, imagery, "
            f"one distinctive detail). Keep each archetype's STRUCTURE intact.\n\n"
            f"BUSINESS:\n{brief}\n\nARCHETYPES:\n{arche_txt}\n\n"
            f"Return ONLY a JSON array of {len(picks)} objects: "
            f'[{{"name":"short name","desc":"2-3 sentence direction, keeping the archetype structure"}}]',
            max_tokens=700, model=CHEAP_MODEL)
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip()); raw = re.sub(r"\s*```$", "", raw)
        items = json.loads(raw)
        out = []
        for i, it in enumerate(items[:len(picks)]):
            nm = it.get("name") or picks[i][0]
            ds = it.get("desc") or picks[i][1]
            out.append((nm, picks[i][1] + " " + ds))   # keep the structural rule + brand tailoring
        if len(out) == len(picks):
            print("  design directions tailored to the brand: " + ", ".join(n for n, _ in out))
            return out
    except Exception:
        pass
    print("  design directions: " + ", ".join(n for n, _ in picks))
    return picks

DIRECTIONS = build_directions(N_PREVIEWS)

FALLBACK_PALETTES = [("#0B1020","#00C2FF","#FFFFFF"), ("#FAF4EC","#C9A24B","#2B1D14"),
                     ("#101418","#7C4DFF","#F5F5F5"), ("#F7F7F5","#1E4080","#15181D"),
                     ("#141414","#E8C4B8","#FAFAF7")]

def fallback_mockup(i):
    """Deterministic, always-renders hero used only if the AI mockup fails twice."""
    bg, accent, fg = FALLBACK_PALETTES[i % len(FALLBACK_PALETTES)]
    img_tag = f'<img src="{PREVIEW_REL}" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.25">' if PREVIEW_REL else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.tailwindcss.com"></script></head>
<body style="margin:0;background:{bg};color:{fg};font-family:system-ui">
<nav style="display:flex;justify-content:space-between;align-items:center;padding:18px 40px;border-bottom:1px solid {accent}33">
 <strong style="letter-spacing:.05em">{answers['company']}</strong>
 <span><a href="#" style="color:{fg};margin-right:22px;text-decoration:none">About</a>
 <a href="#" style="background:{accent};color:{bg};padding:10px 18px;border-radius:10px;text-decoration:none">{answers['cta']}</a></span></nav>
<section style="position:relative;min-height:620px;display:flex;align-items:center;overflow:hidden">
 {img_tag}
 <div style="position:relative;max-width:640px;padding:60px 40px">
  <div style="color:{accent};letter-spacing:.15em;font-size:12px;text-transform:uppercase;margin-bottom:14px">{answers['industry']}</div>
  <h1 style="font-size:56px;line-height:1.1;margin:0 0 18px">{answers['tagline'] if answers['tagline'] not in ('', '(not specified)') else answers['company']}</h1>
  <p style="opacity:.85;line-height:1.6;margin:0 0 26px">{answers['industry']} — built for {answers['audience']}.</p>
  <a href="#" style="background:{accent};color:{bg};padding:14px 26px;border-radius:12px;text-decoration:none;font-weight:600">{answers['cta']}</a>
 </div></section></body></html>"""

def page_valid(html):
    """A generated site page must be complete and have real content."""
    if len(html) < 2500: return False
    low = html.lower()
    if "</html>" not in low and "</body>" not in low: return False
    if not re.search(r"<h[12][\s>]", low): return False
    return True

def mockup_valid(html):
    if len(html) < 1200: return False
    low = html.lower()
    if "</html>" not in low and "</body>" not in low: return False   # truncated
    if not re.search(r"<h[12][\s>]", low): return False              # no visible headline
    return True

# Each preview also gets a DIFFERENT typographic + accent treatment and a different copy angle,
# so the three designs don't just differ in skeleton — they read as three different brands' takes.
TREATMENTS = [
    ("Editorial serif", "Large elegant SERIF headline (high contrast, tight leading, mixed case). Small "
     "uppercase letter-spaced eyebrow. Restrained accent: color used ONLY on the primary button and one "
     "small detail. Generous whitespace, thin hairline rules."),
    ("Brutal sans", "Enormous heavy SANS-SERIF headline in ALL CAPS or tight bold case, very tight leading, "
     "possibly a hard color-block behind the text. Accent used BOLDLY: large solid blocks, filled buttons, "
     "strong contrast. Confident, loud, minimal decoration."),
    ("Modern geometric", "Clean geometric sans headline, medium weight, wide comfortable leading, a soft "
     "gradient or tinted panel. Accent used moderately: gradient touches, rounded pill buttons, subtle "
     "glow/shadow. Contemporary and friendly."),
    ("Condensed display", "Tall CONDENSED display headline, dramatic scale contrast against small body text. "
     "Accent as a thin underline/marker highlight. Layered, magazine-like."),
    ("Mono technical", "Monospace or technical-feeling type, small precise labels, grid lines visible, "
     "understated accent used as markers/ticks. Precise and engineered."),
]

COPY_ANGLES = [
    "Lead with the OUTCOME the customer gets (benefit-first).",
    "Lead with a bold PROVOCATIVE statement or point of view.",
    "Lead with WHO they are and what makes them different (identity-first).",
    "Lead with a specific PROOF POINT (a number, a credential, a result).",
    "Lead with an INVITATION / direct address to the reader.",
]

# shuffle so the treatment/angle pairing differs between runs too
random.shuffle(TREATMENTS)
random.shuffle(COPY_ANGLES)

def make_mockup(i, direction):
    dname, ddesc = direction if isinstance(direction, tuple) else ("Design", direction)
    prompt = f"""Design ONE hero/landing screen (above-the-fold only) for this brand.
This is a DESIGN MOCKUP the client will choose from. It MUST look clearly different from the other
directions — different LAYOUT, not just different text.

BRIEF:
{brief}

COLORS TO USE (apply these exactly — buttons/accents use the primary color, NOT purple/blue defaults):
{answers['palette']}
FONTS TO USE: {answers['fonts']}

DESIGN DIRECTION — "{dname}":
{ddesc}

TYPOGRAPHIC + ACCENT TREATMENT (must be clearly different from other designs) — "{TREATMENTS[i % len(TREATMENTS)][0]}":
{TREATMENTS[i % len(TREATMENTS)][1]}

HERO COPY ANGLE (write ORIGINAL copy for this angle — do NOT just reuse the company tagline verbatim):
{COPY_ANGLES[i % len(COPY_ANGLES)]}
Write a DIFFERENT headline and subline than an obvious restatement of the tagline. It must still be true
to the business, but this design's headline should read differently from the other designs' headlines.

Express this direction strongly; do not fall back to a generic dark full-bleed photo hero unless the
direction explicitly says so.

Requirements:
- ONE screen: a nav bar (logo + links) + a hero section. The hero MUST contain VISIBLE TEXT directly
  in the HTML: a real headline, a one-line subline, and at least one CTA button. Write real copy for
  THIS company — never leave the hero empty or relying only on a background image.
- Hero visual: {"an image is available at " + PREVIEW_REL + " — use it ONLY if this direction calls for a photo (e.g. as a framed accent or a tinted full-width background per the direction). Some directions use a solid color block or minimal image instead — follow the direction." if PREVIEW_REL else "use a styled CSS gradient/color-block panel from the palette (no external image URLs)"}
  Always place the headline/subline/buttons as real visible text, so the screen is never blank.
- ALL content must be visible immediately on load WITHOUT JavaScript: no opacity-0 classes, no
  animation-delayed reveals, no elements that require JS to appear.
- The hero section height should be about 600-700px (use min-height:600px) — NOT 100vh.
- Do NOT rely on JavaScript to render content; all text must be present in the static HTML.
- Single self-contained HTML (CSS in <style>). Tailwind via CDN. Google Fonts.
- Make it look like a real, polished website hero — not a wireframe.
- Return ONLY the HTML starting with <!DOCTYPE html>. No markdown, no commentary."""
    html = clean_html(chat(prompt, max_tokens=6000, model=PREVIEW_MODEL))
    if not mockup_valid(html):
        html = clean_html(chat(prompt + "\n\nIMPORTANT: your previous attempt was incomplete. Output a COMPLETE, "
                               "self-contained HTML file that ends with </html>. Keep it compact.",
                               max_tokens=6000, model=PREVIEW_MODEL))
    if not mockup_valid(html):
        print(f"    design {i+1}: AI output invalid twice — using guaranteed fallback design")
        html = fallback_mockup(i)
    return i, html

mockups = [None] * N_PREVIEWS
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    futures = [ex.submit(make_mockup, i, d) for i, d in enumerate(DIRECTIONS[:N_PREVIEWS])]
    for f in concurrent.futures.as_completed(futures):
        i, html = f.result()
        pathlib.Path(f"mockup_{i+1}.html").write_text(html, encoding="utf-8")
        print(f"  design {i+1} ready")

# build a gallery page that embeds each mockup in an iframe, scaled down like a thumbnail
tiles = ""
for i in range(N_PREVIEWS):
    tiles += f"""
    <div style="border:1px solid #e3e3e3;border-radius:14px;overflow:hidden;background:#fff;box-shadow:0 6px 20px #0001">
      <div style="padding:10px 16px;font:600 14px sans-serif;background:#111;color:#fff;display:flex;justify-content:space-between">
        <span>Design {i+1}</span><a href="mockup_{i+1}.html" target="_blank" style="color:#9cf;text-decoration:none">open full ↗</a>
      </div>
      <div class="thumb">
        <iframe class="frame" src="mockup_{i+1}.html" scrolling="no"></iframe>
      </div>
    </div>"""

gallery = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Choose a design</title>
<style>
  body{{font-family:sans-serif;max-width:1100px;margin:30px auto;padding:0 20px;background:#f6f6f6}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
  .thumb{{position:relative;width:100%;aspect-ratio:1200/700;overflow:hidden;background:#fff}}
  .frame{{position:absolute;top:0;left:0;width:1200px;height:700px;border:0;
          transform-origin:top left;pointer-events:none}}
</style></head><body>
<h1>Choose a design for {answers['company']}</h1>
<p style="color:#666">Different looks based on your answers. Click "open full" to see one bigger,
then type its number in the terminal.</p>
<div class="grid">{tiles}</div>
<script>
  function fit(){{
    document.querySelectorAll('.thumb').forEach(t=>{{
      const f=t.querySelector('.frame');
      f.style.transform='scale('+(t.clientWidth/1200)+')';
    }});
  }}
  window.addEventListener('load',fit);
  window.addEventListener('resize',fit);
  setTimeout(fit,400);
</script>
</body></html>"""
pathlib.Path("designs.html").write_text(gallery, encoding="utf-8")
webbrowser.open("designs.html")

print("\nOpened designs.html — 5 website designs to compare.")
while True:
    pick = input(f"\nWhich design do you want? (1-{N_PREVIEWS}) > ").strip()
    if pick.isdigit() and 1 <= int(pick) <= N_PREVIEWS:
        chosen_idx = int(pick) - 1; break
    print(f"  Pick 1-{N_PREVIEWS}.")

chosen_mockup = pathlib.Path(f"mockup_{chosen_idx+1}.html").read_text(encoding="utf-8")
print(f"\nChosen: Design {chosen_idx+1}")

# the chosen mockup's own code IS the design spec — pages must match its look
template_spec = f'''CHOSEN DESIGN — the full site must match the look, colors, fonts, nav, and feel
of this exact hero mockup the client picked. Here is its full HTML; reuse its palette,
typography, nav styling, button styling, and overall aesthetic on every page:

--- CHOSEN MOCKUP HTML START ---
{chosen_mockup}
--- CHOSEN MOCKUP HTML END ---'''
template_spec += f"""

THEME IMPLEMENTATION:
- If theme mode is "Light + dark": implement a WORKING toggle — define both themes as CSS variables on
  :root and [data-theme="dark"], a visible toggle button in the nav whose click flips
  document.documentElement.dataset.theme, persist the choice with localStorage, and default to the
  user's prefers-color-scheme. Every color on the page must come from the variables so BOTH themes
  fully work. A toggle that does nothing is a failure.
- If theme mode is a single mode (light OR dark): build only that theme and do NOT show any toggle.

USER'S EXPLICIT CHOICES (these OVERRIDE anything in the mockup if they conflict):
- COLORS: {answers['palette']}
- FONTS: {answers['fonts']}
- THEME MODE: {answers['theme']}"""

# ============================================================
#  ENGINE CHOICE  (after the design is picked)
#  OpenRouter = downloadable HTML files | v0 = deployed live URL
# ============================================================
engine = ask_choice("Build the full site with:",
    ["Claude via OpenRouter (HTML files you can download)",
     "v0 by Vercel (deploy the chosen design as a live URL)"])

if engine.startswith("v0"):
    V0_KEY = os.getenv("V0_API_KEY")
    if not V0_KEY:
        print("\nNo V0_API_KEY in .env — add:  V0_API_KEY=v1:team_...  and rerun.")
        raise SystemExit
    V0 = "https://api.v0.dev/v1"
    VH = {"Authorization": f"Bearer {V0_KEY}", "Content-Type": "application/json"}

    pages_desc = "\n".join(
        f"- {pg['name']}{' (homepage)' if pg.get('is_home') else ''}: sections — {', '.join(pg['sections'])}"
        for pg in plan_obj["pages"])

    # v0 cannot see our local files: drop <img> tags and CSS url() that point at local assets
    chosen_mockup_for_v0 = re.sub(r'<img[^>]*src=["\'](?!https?:)[^"\']*["\'][^>]*>', "", chosen_mockup, flags=re.I)
    chosen_mockup_for_v0 = re.sub(r'url\(["\']?(?!https?:)[^)"\']*\.(?:png|jpg|jpeg|webp)["\']?\)',
                                  "none", chosen_mockup_for_v0, flags=re.I)

    v0_prompt = f"""Build a polished multi-page marketing website that MATCHES the design the client already chose.

MATCH THIS EXACT LOOK (colors, fonts, nav style, button style, overall aesthetic) from this hero mockup.
NOTE: any local image paths in it (e.g. preview_hero.png, assets/*.png) are NOT available to you —
ignore them and source your own imagery instead (see IMAGES below).
--- CHOSEN DESIGN HTML ---
{chosen_mockup_for_v0}
--- END ---

BRIEF:
{brief}

PAGES — build EXACTLY these pages, with EXACTLY these names. This is mandatory:
{pages_desc}

PAGE NAMING RULES (critical):
- Use the EXACT page names listed above in the nav, page titles, and all links. Do NOT rename them,
  do NOT substitute "better" names, do NOT merge or drop any page.
- If a page name looks unusual, use it anyway — it is the client's chosen name.
- The nav must contain one link per page above, and nothing else.
- Build every page listed, each with its own sections as listed.

REQUIREMENTS:
- Colors: {answers['palette']}
- Fonts: {answers['fonts']}
- Theme: {answers['theme']} (if light+dark, include a WORKING toggle)
- Animation level: {answers['animation']}
- Every CTA links to the contact/booking page; that page has a working validated form plus the
  company's location & hours.
- Unique layout/content per page, responsive, accessible, SEO meta + Open Graph on every page.

IMAGES — MANDATORY. The site must contain REAL GENERATED PHOTOS, not placeholders:
- GENERATE actual images with your image generation capability for this specific business.
- Every page needs real photos: a hero image, and images for cards/grids/gallery/team sections.
- DO NOT use gradient panels, solid color blocks, empty divs, or CSS-only placeholders in place of
  photos. DO NOT reference local file paths. A site with no real images is a FAILED result.
- Each generated image must be specific to this business and this section (e.g. for a creative studio:
  the studio space, the team working, actual project/portfolio visuals).
- Use a DIFFERENT image for every section; never repeat the same image twice.
- Add descriptive alt text to every image.
"""
    def v0_post(url, body):
        r = requests.post(url, headers=VH, json=body, timeout=60)
        if r.status_code != 200:
            print(f"  v0 error HTTP {r.status_code}: {r.text[:300]}"); raise SystemExit
        return r.json()

    print("\nCreating v0 project...")
    project = v0_post(f"{V0}/projects", {"name": (answers["company"] or "License-to-Launch")[:60]})
    print("Generating with v0-pro (a few minutes)...")
    chat = v0_post(f"{V0}/chats", {"message": v0_prompt, "responseMode": "async",
                                   "modelConfiguration": {"modelId": "v0-pro"},
                                   "projectId": project["id"]})
    chat_id = chat["id"]
    print("  edit on v0:", chat.get("webUrl"))

    version_id = None
    MAX_WAIT_MIN = 30
    polls = (MAX_WAIT_MIN * 60) // 10
    print(f"  v0 is generating a full multi-page site — this usually takes 5-20 minutes.")
    print(f"  (waiting up to {MAX_WAIT_MIN} min; you can watch live at the edit link above)")
    for i in range(polls):
        time.sleep(10)
        g = requests.get(f"{V0}/chats/{chat_id}", headers=VH, timeout=30)
        if g.status_code != 200:
            print(f"  [{(i+1)*10//60}m{(i+1)*10%60:02d}s] waiting (HTTP {g.status_code})"); continue
        data = g.json()
        v = data.get("latestVersion") or {}
        st = (v.get("status") or data.get("status") or v.get("state"))
        demo = v.get("demoUrl")
        vid = v.get("id") or data.get("latestVersionId")
        elapsed = f"{(i+1)*10//60}m{(i+1)*10%60:02d}s"

        if st in ("failed", "error"):
            print(f"  [{elapsed}] v0 generation FAILED."); raise SystemExit

        # done when we have a version id AND a demo url (or an explicit completed status)
        if (st in ("completed", "ready", "done") and vid) or (vid and demo):
            version_id = vid
            print(f"  [{elapsed}] generation complete")
            if demo:
                print("  instant preview:", demo)
            break

        label = st if st else "generating"
        print(f"  [{elapsed}] {label}...")
    if not version_id:
        print(f"\nStill not finished after {MAX_WAIT_MIN} min.")
        print("v0 may still be working — open the edit link above; if the site is there,")
        print("you can deploy it manually from the v0 interface.")
        raise SystemExit

    print("\nDeploying...")
    dep = v0_post(f"{V0}/deployments", {"chatId": chat_id, "versionId": version_id,
                                        "projectId": project["id"]})
    d = requests.get(f"{V0}/deployments/{dep['id']}", headers=VH, timeout=30).json()
    print("\n=== LIVE SITE ===")
    print(d.get("webUrl") or dep.get("webUrl") or "(no URL — check inspector)")
    print("inspector:", d.get("inspectorUrl", ""), "\n")
    raise SystemExit

# ============================================================
#  STEP 2.5 — IMAGE SOURCE  (customer photos  OR  AI-generated)
# ============================================================
image_catalog = ""   # text the page-builder will read to know what images to use
logo_path = ""       # relative path to the company logo, if found (used as favicon)

img_mode = ask_choice("Where should the website's photos come from?",
    ["Use my own photos (from the uploaded profile)",
     "Generate photos with AI (custom images for this brand)"])

SITE_DIR.mkdir(exist_ok=True)

did_own = False
if img_mode.startswith("Use my own"):
    imgs = extract_images_from_file(profile_path) if profile_path else []
    if not imgs:
        print("\n  No usable images found in the profile — switching to AI-generated photos.")
    else:
        print(f"\n  Found {len(imgs)} image(s). Labeling them with AI vision...")
        lines = []
        for fp in imgs:
            label = label_image(fp)
            rel = f"assets/{fp.name}"
            print(f"    {rel}  ->  {label}")
            lines.append(f'- "{rel}"  ({label})')
            if "logo" in label.lower() and not logo_path:
                logo_path = rel
                print(f"    ^ using this as the site logo (nav + favicon)")
        image_catalog = ("USE THESE REAL CLIENT IMAGES (reference them by these exact relative paths; "
                         "put the logo in the nav, product/service photos in grids/cards, etc.). "
                         "Only if you need MORE images than provided, reuse the provided images or leave those spots as simple styled color blocks:\n"
                         + "\n".join(lines))
        did_own = True

USE_AI_IMAGES = False
if not did_own:
    # AI images are generated PER PAGE later (in the build loop) so each page gets its OWN unique photos.
    USE_AI_IMAGES = True
    image_catalog = ""  # filled per-page during the build
    print("\n  AI images will be generated per page during the build (unique images per page).")

# ============================================================
#  (page structure comes from the user — see PAGE & SECTION BUILDER above)
# ============================================================

# ============================================================
#  STEP 4 — BUILD THE PAGES FROM THE APPROVED PLAN
# ============================================================
nav_links = " | ".join(f"{label} -> {slugs[label]}.html" for label in pages)

# one-line summary of every page (so each page knows what the OTHERS cover and won't repeat them)
def page_summary(pg):
    secs = "; ".join(pg.get("sections", [])[:4])
    return f"{pg['name']} ({slugs[pg['name']]}.html): {secs}"
site_map = "\n".join("- " + page_summary(pg) for pg in plan_obj["pages"])

out_dir = SITE_DIR; out_dir.mkdir(exist_ok=True)

# pages, home first
home_name = next(pg["name"] for pg in plan_obj["pages"] if slugs[pg["name"]] == "index")
ordered = [home_name] + [n for n in pages if n != home_name]

def sections_for(label):
    for pg in plan_obj["pages"]:
        if pg["name"] == label:
            return "\n".join(f"- {s}" for s in pg.get("sections", []))
    return ""

def extract_shell(html):
    """Pull the <nav>...</nav> and <footer>...</footer> blocks from the homepage."""
    nav = re.search(r"<nav\b.*?</nav>", html, re.S | re.I)
    foot = re.search(r"<footer\b.*?</footer>", html, re.S | re.I)
    return (nav.group(0) if nav else ""), (foot.group(0) if foot else "")

common_rules = f"""
BRIEF:
{brief}

{template_spec}

{DESIGN_SYSTEM}

IMAGES:
{image_catalog}

WHOLE-SITE MAP (every page and what it covers — do NOT put another page's content on this page):
{site_map}

Reuse the exact Google Fonts and color palette from the chosen mockup so all pages match.
Output a SINGLE self-contained HTML file (CSS in <style>, JS in <script>).
Return ONLY the HTML starting with <!DOCTYPE html>. No markdown, no commentary.
"""

print("\nBuilding pages (homepage first)...\n")
nav_html = footer_html = ""

# figure out which page is the order/contact destination for all CTAs
def is_order_page(name):
    n = name.lower()
    return any(w in n for w in ["order", "contact", "book", "reserve", "visit", "get in touch", "enquir", "inquir"])
order_label = next((n for n in pages if is_order_page(n)), pages[-1])
ORDER_PAGE = slugs[order_label] + ".html"
CTA_RULE = (f"Every primary call-to-action button (e.g. '{answers['cta']}', 'Order', 'Book', 'Contact') "
            f"MUST be a working link to \"{ORDER_PAGE}\" (use <a href=\"{ORDER_PAGE}\">). "
            f"Never leave a CTA as href=\"#\" or a dead button.")
print(f"  all CTAs will link to: {ORDER_PAGE}")

LOGO_RULE = (
    f'BRAND LOGO: the company logo image is at "{logo_path}". Put it in the TOP-LEFT of the nav bar on '
    f'EVERY page as <img src="{logo_path}" alt="{answers["company"]} logo"> (height ~40px, width auto), '
    f'wrapped in a link to the homepage. You may place the company name beside it, but the logo image '
    f'itself must appear. Also use it in the footer. Do NOT invent a text-only or icon logo.'
) if logo_path else (
    f'BRAND LOGO: no logo image was provided — create a clean text-based wordmark for '
    f'"{answers["company"]}" in the top-left of the nav (optionally with a small icon shape).'
)
print(f"  logo: {'using ' + logo_path if logo_path else 'text wordmark (none provided)'}")

if USE_AI_IMAGES:
    # guarantee: every page gets at least one image spec even if the plan omitted them
    for pg in plan_obj["pages"]:
        if not pg.get("images"):
            first_sec = (pg.get("sections") or ["main section"])[0]
            pg["images"] = [{"section": first_sec,
                             "desc": f"{answers['industry']} — photo for the {pg['name']} page ({first_sec})"}]
    total_specs = sum(len(pg.get("images") or []) for pg in plan_obj["pages"])
    print(f"  image specs in plan: {total_specs}")
page_image_catalogs = generate_all_page_images(plan_obj, slugs) if USE_AI_IMAGES else {}
if USE_AI_IMAGES and not page_image_catalogs:
    print("  WARNING: no images were generated — pages will use styled panels instead.")

CTA_WORDS = re.compile(r"order|book|reserve|contact|call|get in touch|enquir|inquir|get started|buy",
                       re.I)

def fix_ctas(html, current_slug=""):
    """Deterministically repair dead CTAs so buttons ALWAYS work:
    1. href="#" / href='' -> order page
    2. href="#fragment" whose link text is a CTA -> order page
    3. <button>CTA text</button> with no onclick -> add onclick redirect
    """
    html = re.sub(r'href="#"', f'href="{ORDER_PAGE}"', html)
    html = re.sub(r"href='#'", f"href='{ORDER_PAGE}'", html)
    html = re.sub(r'href=""', f'href="{ORDER_PAGE}"', html)

    def anchor_fix(m):
        text = re.sub(r"<[^>]+>", "", m.group(3))
        if CTA_WORDS.search(text):
            return f'<a{m.group(1)}href="{ORDER_PAGE}"{m.group(2)}>{m.group(3)}</a>'
        return m.group(0)
    html = re.sub(r'<a([^>]*?)href=["\']#[^"\']*["\']([^>]*)>(.*?)</a>',
                  anchor_fix, html, flags=re.S | re.I)

    def button_fix(m):
        attrs, text = m.group(1), m.group(2)
        plain = re.sub(r"<[^>]+>", "", text)
        if CTA_WORDS.search(plain) and "onclick" not in attrs.lower() and "submit" not in attrs.lower():
            return f'<button{attrs} onclick="window.location.href=\'{ORDER_PAGE}\'">{text}</button>'
        return m.group(0)
    html = re.sub(r'<button([^>]*)>(.*?)</button>', button_fix, html, flags=re.S | re.I)
    return html

def strip_breadcrumbs(html):
    """Remove breadcrumb bars and any second <nav> — the injected nav is the only navigation."""
    html = re.sub(r'<(nav|div|ol|ul)[^>]*(breadcrumb|aria-label=["\']breadcrumb)[^>]*>.*?</\1>',
                  "", html, flags=re.S | re.I)
    navs = list(re.finditer(r"<nav\b.*?</nav>", html, re.S | re.I))
    if len(navs) > 1:
        # keep the first nav (header) and any nav inside the footer; drop others
        foot = re.search(r"<footer\b.*?</footer>", html, re.S | re.I)
        fspan = foot.span() if foot else (-1, -1)
        for m in reversed(navs[1:]):
            if not (fspan[0] <= m.start() <= fspan[1]):
                html = html[:m.start()] + html[m.end():]
    return html

def fix_duplicate_images(html):
    """If the same image is used more than once on a page, keep the FIRST use and
    replace later <img> repeats with a styled gradient panel (no more identical photos everywhere)."""
    seen = {}
    def img_fix(m):
        tag = m.group(0)
        srcm = re.search(r'src=["\']([^"\']*assets/[^"\']+)["\']', tag)
        if not srcm:
            return tag
        src_ = srcm.group(1)
        seen[src_] = seen.get(src_, 0) + 1
        if seen[src_] > 1:
            return ('<div aria-hidden="true" style="width:100%;min-height:220px;border-radius:1rem;'
                    'background:linear-gradient(135deg, rgba(0,0,0,.08), rgba(0,0,0,.22));"></div>')
        return tag
    return re.sub(r'<img[^>]*>', img_fix, html, flags=re.I)

def sections_list(label):
    for pg in plan_obj["pages"]:
        if pg["name"] == label:
            return pg.get("sections", [])
    return []

def forbidden_for(label):
    mine = set(s.lower() for s in (next(pg.get("sections", []) for pg in plan_obj["pages"] if pg["name"] == label) or []))
    other = []
    for pg in plan_obj["pages"]:
        if pg["name"] == label: continue
        for s in pg.get("sections", []):
            if s.lower() not in mine:
                other.append(f"{s} (belongs to the {pg['name']} page)")
    return "\n".join(f"- {o}" for o in other) or "- (none)"

def build_page_prompt(label, slug, page_images):
    if slug == "index":
        return f"""Build the HOMEPAGE ("{label}", file: index.html) of a multi-page site.
{common_rules}

This page's sections (build ONLY these — this is the homepage, so it gets the main hero):
{sections_for(label)}

STRICTLY FORBIDDEN ON THIS PAGE — these topics belong to OTHER pages and must NOT appear here
(no pricing tables, membership tiers, forms, galleries, etc. unless listed in THIS page's sections above):
{forbidden_for(label)}

IMAGES FOR THIS PAGE:
{page_images}
{blueprints_for(sections_list(label))}

CALL-TO-ACTION RULE:
{CTA_RULE}

{LOGO_RULE}

SEO REQUIREMENTS:
- A unique, descriptive <title> for this page: "{label} — {answers['company']}".
- A <meta name="description"> (max 155 chars) summarizing THIS page for search results.
- Open Graph tags: og:title, og:description, og:type ("website"), and og:image if this page has an image.
- One single <h1> per page; use h2/h3 for the rest. Descriptive alt text on every image.

NAV: a sticky nav linking to these pages by exact file name: {nav_links}
Highlight "{label}" as active. Include a matching footer.
"""
    return f"""Build the "{label}" page (file: {slug}.html) of a multi-page site.
{common_rules}

CRITICAL RULES:
- THIS PAGE IS CALLED "{label}". Use that exact name in the nav, the page title, headings, and all copy.
  Never substitute a generic name (e.g. do not call it "Blog" if it is named something else).
- Build ONLY this page's own sections (listed below). Do NOT add sections that belong to other pages
  (no booking on a team page, no team on a vision page, etc.). This is its OWN dedicated page.
- This is an INNER page, NOT the homepage: do NOT copy the homepage's big hero. Use a smaller,
  distinct page-header for this page, then this page's unique content with its OWN layout.
- Make the layout visibly different from the other pages while keeping the same colors/fonts.
- Do NOT add any breadcrumb bar or secondary navigation of any kind — the provided nav is the ONLY navigation on the page.

This page's sections (build exactly these):
{sections_for(label)}

STRICTLY FORBIDDEN ON THIS PAGE — these topics belong to OTHER pages and must NOT appear here
(no pricing tables, membership tiers, forms, galleries, etc. unless listed in THIS page's sections above):
{forbidden_for(label)}
{'THIS IS THE CONTACT/BOOKING PAGE: it MUST contain a working booking/contact form (name, email, message/date, with JS validation and a visible success state) AND a clear location section with the company address, opening hours, and an embedded map placeholder.' if slug == slugs[order_label] else ''}

IMAGES FOR THIS PAGE (unique to this page):
{page_images}
{blueprints_for(sections_list(label))}

CALL-TO-ACTION RULE:
{CTA_RULE}

{LOGO_RULE}

SEO REQUIREMENTS:
- A unique, descriptive <title> for this page: "{label} — {answers['company']}".
- A <meta name="description"> (max 155 chars) summarizing THIS page for search results.
- Open Graph tags: og:title, og:description, og:type ("website"), and og:image if this page has an image.
- One single <h1> per page; use h2/h3 for the rest. Descriptive alt text on every image.

USE THIS EXACT NAV (paste it as-is, but change which link is marked active to "{label}"):
{nav_html}

USE THIS EXACT FOOTER (paste it as-is):
{footer_html}
"""

def generate_with_retry(prompt, label):
    html = clean_html(chat(prompt, max_tokens=16000))
    if not page_valid(html):
        print(f"     {label}: output incomplete — regenerating once")
        html = clean_html(chat(prompt + "\n\nIMPORTANT: your previous attempt was incomplete. "
                               "Output a COMPLETE self-contained HTML file ending with </html>.",
                               max_tokens=16000))
    return html

AOS_FAILSAFE = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
    "document.querySelectorAll('[data-aos]').forEach(function(el){"
    "var cs=getComputedStyle(el);if(cs.opacity==='0'||cs.visibility==='hidden'){"
    "el.style.opacity='1';el.style.transform='none';el.style.visibility='visible';}});if(window.lucide){try{lucide.createIcons();}catch(e){}}},1500);});</script>")

def fix_tailwind_classes(html):
    """Snap off-scale Tailwind spacing/sizing utilities to the nearest valid value.
    In strict Tailwind builds an unknown class can break the whole stylesheet -> blank page.
    Valid default scale: 0,0.5,1,1.5,2,2.5,3,3.5,4,5,6,7,8,9,10,11,12,14,16,20,24,28,32,...
    """
    VALID = [0,0.5,1,1.5,2,2.5,3,3.5,4,5,6,7,8,9,10,11,12,14,16,20,24,28,32,36,40,44,48,52,56,60,64,72,80,96]
    prefixes = ("h","w","p","pt","pb","pl","pr","px","py","m","mt","mb","ml","mr","mx","my",
                "gap","gap-x","gap-y","space-x","space-y","top","bottom","left","right","inset",
                "size","min-h","min-w","max-h","max-w","leading","text")
    pref_alt = "|".join(sorted((re.escape(p) for p in prefixes), key=len, reverse=True))
    # matches optional responsive/state prefix (lg:, hover:, etc.), then prefix-number
    pat = re.compile(r'((?:[a-z0-9-]+:)*)(' + pref_alt + r')-(\d+(?:\.\d+)?)\b')

    def nearest(n):
        return min(VALID, key=lambda v: (abs(v - n), -v))

    def repl(m):
        variant, pref, num = m.group(1), m.group(2), m.group(3)
        try:
            val = float(num)
        except ValueError:
            return m.group(0)
        if val in VALID:
            return m.group(0)                      # already valid
        # leave through-scale utilities that legitimately take arbitrary ints (grid cols, z, order, etc.)
        if pref in ("text",) and val >= 100:       # text-100..text-900 are font-weight-ish/color shades -> skip
            return m.group(0)
        snapped = nearest(val)
        snapped_str = str(int(snapped)) if snapped == int(snapped) else str(snapped)
        return f"{variant}{pref}-{snapped_str}"

    return pat.sub(repl, html)

def postprocess_and_save(label, slug, html):
    html = fix_ctas(html)
    html = fix_duplicate_images(html)
    html = strip_breadcrumbs(html)
    html = fix_tailwind_classes(html)
    if logo_path:
        favicon = f'<link rel="icon" href="{logo_path}">'
        if "rel=\"icon\"" not in html:
            if re.search(r"</head>", html, re.I):
                html = re.sub(r"</head>", favicon + "\n</head>", html, count=1, flags=re.I)
            else:
                html = favicon + "\n" + html
    if "</body>" in html:
        html = html.replace("</body>", AOS_FAILSAFE + "\n</body>", 1)
    else:
        html += AOS_FAILSAFE
    (out_dir / f"{slug}.html").write_text(html, encoding="utf-8")
    print(f"  done: {label} ({slug}.html)")

# ---- homepage first (its nav/footer feed every other page) ----
home_images = page_image_catalogs.get(home_name, image_catalog) if USE_AI_IMAGES else image_catalog
print(f"  -> {home_name} (index.html)")
html = generate_with_retry(build_page_prompt(home_name, "index", home_images), home_name)
nav_html, footer_html = extract_shell(html)
postprocess_and_save(home_name, "index", html)

# ---- all inner pages IN PARALLEL (much faster) ----
inner = [n for n in ordered if slugs[n] != "index"]
print(f"  building {len(inner)} inner pages in parallel...")
import concurrent.futures as _cf
def _build_inner(label):
    slug = slugs[label]
    imgs = page_image_catalogs.get(label, image_catalog) if USE_AI_IMAGES else image_catalog
    html = generate_with_retry(build_page_prompt(label, slug, imgs), label)
    postprocess_and_save(label, slug, html)
with _cf.ThreadPoolExecutor(max_workers=4) as ex:
    list(ex.map(_build_inner, inner))

print(f"\nDone. {len(pages)} pages saved in ./{SITE_DIR}/")
print(f"Open the site:  start {SITE_DIR}\\index.html")
import shutil
zip_path = shutil.make_archive(str(SITE_DIR), "zip", root_dir=str(SITE_DIR))
print(f"Ready to share:  {pathlib.Path(zip_path).name}  (send this zip, or drag the {SITE_DIR} folder onto netlify.com)")
print(f"\nAPI usage this run:  {CALLS['main']} calls on {MODEL.split('/')[-1]}  |  "
      f"{CALLS['cheap']} on {CHEAP_MODEL.split('/')[-1]}  |  {CALLS['image']} images")
webbrowser.open(str(out_dir / "index.html"))