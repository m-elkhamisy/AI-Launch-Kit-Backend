"""Deterministic industry-specific design direction fallback."""

# ruff: noqa: E501

from launchkit.intake.models import OnboardingForm

_INDUSTRY_PRESETS: tuple[tuple[str, str], ...] = (
    (
        "bakery",
        "Warm Parisian patisserie feel: cream, gold, espresso tones, elegant serifs, soft light imagery, indulgent copy. Menu grids with prices, 'order' CTAs.",
    ),
    (
        "food",
        "Warm, appetizing, artisanal. Close-up textures, warm tones, serif elegance. Menu-style product grids with prices.",
    ),
    (
        "restaurant",
        "Appetite-driven: rich food photography, warm palette, menu sections with prices, reservation CTAs, chef/story highlight.",
    ),
    (
        "cafe",
        "Cozy and inviting: warm neutrals, casual serif/sans mix, menu boards, location & hours prominent, community feel.",
    ),
    (
        "catering",
        "Elegant abundance: spread/platter imagery, event-focused sections, package tiers, enquiry CTAs.",
    ),
    (
        "hotel",
        "Serene luxury: full-width imagery, airy spacing, room/amenity cards, booking CTAs, location highlights.",
    ),
    (
        "travel",
        "Aspirational: immersive full-width imagery, light airy type, destination cards, itinerary highlights, 'book now' CTAs.",
    ),
    (
        "law",
        "Restrained authority: serif headings, navy/charcoal palette, generous whitespace, credential and results sections, trust signals.",
    ),
    (
        "consulting",
        "Professional clarity: structured grids, muted palette with one strong accent, case-study cards, process timelines, outcome metrics.",
    ),
    (
        "accounting",
        "Precise and trustworthy: clean grids, navy/green tones, service cards, compliance badges, consultation CTAs.",
    ),
    (
        "finance",
        "Confident stability: deep blues, structured layout, metric stat strips, service tiers, regulatory trust signals.",
    ),
    (
        "insurance",
        "Reassuring clarity: calm palette, plan-comparison cards, claim-process steps, quote CTAs.",
    ),
    (
        "marketing",
        "Bold creativity: vivid accent colors, striking type, portfolio grid, results metrics, punchy copy.",
    ),
    (
        "agency",
        "Portfolio-forward: large case-study imagery, confident typography, client logos strip, project inquiry CTAs.",
    ),
    (
        "recruitment",
        "People-focused: friendly photography, role/category cards, process steps, employer & candidate dual CTAs.",
    ),
    (
        "health",
        "Calm and trustworthy: soft blues/greens, airy spacing, rounded shapes, friendly photography, clear service cards, appointment CTAs.",
    ),
    (
        "clinic",
        "Clean medical trust: white space, soft blue accents, doctor/team cards, services grid, easy booking.",
    ),
    (
        "dental",
        "Bright and reassuring: white/teal palette, smile photography, treatment cards, before/after, booking CTAs.",
    ),
    (
        "pharmacy",
        "Clean and accessible: green/white tones, product categories, health-tip sections, location & hours prominent.",
    ),
    (
        "fitness",
        "Energetic: bold condensed headlines, high-contrast dark sections, action photography, program cards, transformation stats.",
    ),
    (
        "beauty",
        "Elegant and sensory: soft pastels or rich jewel tones, refined serifs, editorial imagery, treatment menus, booking CTAs.",
    ),
    (
        "salon",
        "Chic and personal: fashion-style imagery, elegant type, service menu with prices, stylist team, booking CTAs.",
    ),
    (
        "spa",
        "Tranquil luxury: muted naturals, airy whitespace, ritual/treatment cards, serene imagery, reservation CTAs.",
    ),
    (
        "real estate",
        "Premium and spacious: large property imagery, clean sans type, dark-on-light luxury feel, listing cards, location highlights.",
    ),
    (
        "construction",
        "Solid and capable: strong slab typography, steel/earth tones, project portfolio grid, capability stats, tender/enquiry CTAs.",
    ),
    (
        "architecture",
        "Minimal gallery feel: large project photography, restrained type, grid portfolio, studio philosophy section.",
    ),
    (
        "interior",
        "Editorial elegance: room photography, refined serif/sans pairing, portfolio grid, design-process steps, consultation CTAs.",
    ),
    (
        "cleaning",
        "Fresh and dependable: bright palette, before/after visuals, service packages with pricing, booking CTAs.",
    ),
    (
        "retail",
        "Product-forward: clean grids, generous product imagery, clear pricing, promo bands, cart-style CTAs.",
    ),
    (
        "trading",
        "Global and capable: professional palette, product-category grid, logistics/partners strip, enquiry CTAs.",
    ),
    (
        "logistics",
        "Motion and reliability: bold type, route/fleet imagery, service cards, coverage map mention, tracking/quote CTAs.",
    ),
    (
        "manufacturing",
        "Industrial strength: dark accents, machinery/facility imagery, capability specs, certifications strip, RFQ CTAs.",
    ),
    (
        "automotive",
        "Sleek and technical: dark palette with metallic accents, vehicle photography, service cards, booking/quote CTAs.",
    ),
    (
        "jewelry",
        "Refined luxury: dark or cream backdrop, macro product photography, serif elegance, collection grids.",
    ),
    (
        "furniture",
        "Warm modern living: lifestyle room imagery, natural tones, collection grids, material/craft story.",
    ),
    (
        "tech",
        "Confident and modern: bold sans headlines, dark or high-contrast sections, gradient accents, product mockups, feature grids, stat strips.",
    ),
    (
        "software",
        "Product-led: clean UI screenshots, feature grids with icons, pricing tiers, integration logos, trial CTAs.",
    ),
    (
        "photography",
        "Image-first: near-fullscreen gallery, minimal type, dark or white gallery backdrop, package tiers, booking CTAs.",
    ),
    (
        "events",
        "Celebratory energy: vibrant imagery, showcase gallery, service packages, testimonial spotlights, enquiry CTAs.",
    ),
    (
        "education",
        "Approachable and structured: friendly type, clear program cards, outcome stats, testimonial spotlights, enrollment CTAs.",
    ),
    (
        "pets",
        "Playful warmth: friendly rounded type, joyful animal photography, service cards, booking CTAs.",
    ),
)


def resolve_industry_style_direction(form: OnboardingForm) -> str:
    """Return the ordered keyword fallback from the TypeScript implementation."""

    haystack = f"{form.industry} {form.business_activity}".lower()
    for key, style in _INDUSTRY_PRESETS:
        if key in haystack:
            return f"INDUSTRY STYLE DIRECTION ({key}): {style}"
    return ""
