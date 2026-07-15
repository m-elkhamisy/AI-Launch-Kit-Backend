"""Stable wizard catalog IDs shared by project validation and API responses."""

from dataclasses import dataclass

from launchkit.design.models import AnimationOption, StyleOption, ThemeOption
from launchkit.design.presets import FONT_PRESETS, PALETTE_PRESETS


@dataclass(frozen=True, slots=True)
class Choice:
    id: str
    label: str
    description: str = ""


BUSINESS_CATEGORIES = (
    Choice("corporate-enterprise", "Corporate Enterprise", "Established and professional."),
    Choice("bookshop", "Bookshop", "Physical and digital books for readers."),
    Choice("coffee-shop", "Coffee Shop", "Cafes and specialty coffeehouses."),
    Choice("education", "Education", "Schools, tutors, courses, and institutions."),
    Choice("healthcare", "Healthcare", "Clinics, practices, and wellness providers."),
    Choice("restaurant", "Restaurant", "Dining, takeaway, and food delivery."),
    Choice("retail-ecommerce", "Retail / E-commerce", "Product stores and online shops."),
    Choice("tech-saas", "Tech / SaaS", "Software, apps, and technology companies."),
    Choice("creative-agency", "Creative Agency", "Design, marketing, and brand studios."),
    Choice("fitness-wellness", "Fitness / Wellness", "Gyms, studios, and coaches."),
    Choice("real-estate", "Real Estate", "Property agents, listings, and developers."),
    Choice("non-profit", "Non-Profit", "Charities, foundations, and communities."),
)

DESIGN_MOODS = (
    Choice("minimalist", "Minimalist", "Clean, airy, and uncluttered."),
    Choice("elegant", "Elegant", "Refined and understated."),
    Choice("bold", "Bold", "High contrast and visually striking."),
    Choice("playful", "Playful", "Friendly, energetic, and approachable."),
    Choice("professional-trustworthy", "Professional & Trustworthy", "Credible and clear."),
    Choice("dark-modern", "Dark & Modern", "Deep backgrounds and a technical feel."),
    Choice("warm-inviting", "Warm & Inviting", "Welcoming colors and textures."),
    Choice("editorial", "Editorial", "Strong typography and magazine-like hierarchy."),
)

MOOD_STYLE_MAP = {
    "minimalist": StyleOption.MODERN,
    "elegant": StyleOption.LUXURY,
    "bold": StyleOption.BOLD,
    "playful": StyleOption.BOLD,
    "professional-trustworthy": StyleOption.CORPORATE,
    "dark-modern": StyleOption.DARK_TECH,
    "warm-inviting": StyleOption.WARM,
    "editorial": StyleOption.LUXURY,
}

ANIMATION_LEVELS = (
    Choice("minimal", "Minimal", "Static with no decorative motion."),
    Choice("low", "Low", "Gentle fades and light movement."),
    Choice("balanced", "Balanced", "Hover effects and scroll reveals."),
    Choice("high", "High", "Rich motion throughout."),
)
ANIMATION_MAP = {
    "minimal": AnimationOption.NONE,
    "low": AnimationOption.SUBTLE,
    "balanced": AnimationOption.MEDIUM,
    "high": AnimationOption.HIGH,
}

THEME_MODES = (
    Choice("light", "Light mode"),
    Choice("dark", "Dark mode"),
    Choice("toggle", "Light + dark"),
)
THEME_MAP = {
    "light": ThemeOption.LIGHT,
    "dark": ThemeOption.DARK,
    "toggle": ThemeOption.TOGGLE,
}


@dataclass(frozen=True, slots=True)
class SectionTemplate:
    id: str
    label: str
    locked: bool = False


SECTION_TEMPLATES = (
    SectionTemplate("navigation", "Navigation", True),
    SectionTemplate("footer", "Footer", True),
    SectionTemplate("hero", "Hero Section"),
    SectionTemplate("features", "Features"),
    SectionTemplate("testimonials", "Testimonials"),
    SectionTemplate("cta", "Call To Action"),
    SectionTemplate("about-hero", "About Hero"),
    SectionTemplate("our-story", "Our Story"),
    SectionTemplate("team", "Team Members"),
    SectionTemplate("values", "Values"),
    SectionTemplate("services-hero", "Services Hero"),
    SectionTemplate("service-cards", "Service Cards"),
    SectionTemplate("pricing", "Pricing"),
    SectionTemplate("faq", "FAQ"),
    SectionTemplate("portfolio-hero", "Portfolio Hero"),
    SectionTemplate("gallery", "Gallery"),
    SectionTemplate("case-studies", "Case Studies"),
    SectionTemplate("blog-hero", "Blog Hero"),
    SectionTemplate("blog-posts", "Blog Posts"),
    SectionTemplate("newsletter", "Newsletter"),
    SectionTemplate("contact-hero", "Contact Hero"),
    SectionTemplate("contact-form", "Contact Form"),
    SectionTemplate("map-location", "Map / Location"),
    SectionTemplate("stats", "Stats"),
    SectionTemplate("partners", "Partners"),
    SectionTemplate("video", "Video"),
)
SECTION_BY_ID = {item.id: item for item in SECTION_TEMPLATES}


@dataclass(frozen=True, slots=True)
class PageTemplate:
    id: str
    label: str
    slug: str
    sections: tuple[str, ...]
    selected_by_default: bool = False


PAGE_TEMPLATES = (
    PageTemplate(
        "home",
        "Home",
        "index",
        ("navigation", "hero", "features", "testimonials", "cta", "footer"),
        True,
    ),
    PageTemplate(
        "about",
        "About Us",
        "about",
        ("navigation", "about-hero", "our-story", "team", "values", "footer"),
        True,
    ),
    PageTemplate(
        "services",
        "Services",
        "services",
        ("navigation", "services-hero", "service-cards", "pricing", "faq", "footer"),
    ),
    PageTemplate(
        "portfolio",
        "Portfolio",
        "portfolio",
        ("navigation", "portfolio-hero", "gallery", "case-studies", "footer"),
    ),
    PageTemplate(
        "blog", "Blog", "blog", ("navigation", "blog-hero", "blog-posts", "newsletter", "footer")
    ),
    PageTemplate(
        "contact",
        "Contact",
        "contact",
        ("navigation", "contact-hero", "contact-form", "map-location", "footer"),
        True,
    ),
    PageTemplate(
        "landing", "Landing Page", "landing", ("navigation", "hero", "features", "cta", "footer")
    ),
    PageTemplate("pricing", "Pricing", "pricing", ("navigation", "pricing", "faq", "footer")),
)
PAGE_BY_ID = {item.id: item for item in PAGE_TEMPLATES}

BUSINESS_CATEGORY_IDS = {item.id for item in BUSINESS_CATEGORIES}
MOOD_IDS = {item.id for item in DESIGN_MOODS}
ANIMATION_IDS = {item.id for item in ANIMATION_LEVELS}
THEME_IDS = {item.id for item in THEME_MODES}
PALETTE_IDS = {item.value for item in PALETTE_PRESETS} | {"ai-choice", "custom"}
FONT_IDS = {item.value for item in FONT_PRESETS} | {"ai-choice", "custom"}
