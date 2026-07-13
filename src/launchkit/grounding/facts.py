"""Render intake data as verified and explicitly missing fact groups."""

from collections.abc import Iterable

from launchkit.intake.models import OnboardingForm


def _fact_block(title: str, fields: Iterable[tuple[str, str]], empty_note: str) -> str:
    given = [(label, value.strip()) for label, value in fields if value.strip()]
    if not given:
        return f"{title}: NOT PROVIDED — {empty_note}"
    lines = [f"{title} (verified, use as-is):"]
    lines.extend(f"  - {label}: {value}" for label, value in given)
    return "\n".join(lines)


def render_fact_sheet(form: OnboardingForm) -> str:
    """Render the Haseeb intake contract without inventing missing facts."""

    sections = (
        _fact_block(
            "IDENTITY",
            (
                ("Company", form.company_name),
                ("Industry", form.industry),
                ("Activity classification", form.activity_code),
                ("What the business does", form.business_activity),
            ),
            "do not invent an industry or business description.",
        ),
        _fact_block(
            "AUDIENCE & POSITIONING",
            (
                ("Target audience", form.target_audience),
                ("Unique value proposition", form.uvp),
                ("Competitors to differentiate from", form.competitors),
                ("Purpose of this site", form.purpose),
            ),
            "keep positioning language generic rather than inventing a differentiator.",
        ),
        _fact_block(
            "PROOF & STATS",
            (
                ("Stats / achievements", form.stats),
                ("Testimonials (real quotes)", form.testimonials),
                ("Team / founders", form.team_bios),
                ("Certifications / awards", form.certifications),
            ),
            "do NOT invent stats, testimonials, team members, or awards. Omit these claims "
            "or use the placeholder approach described in FACTUAL DISCIPLINE.",
        ),
        _fact_block(
            "PRACTICAL DETAILS",
            (
                ("Products / services", form.products),
                ("Location & hours", form.location_hours),
                ("Service area", form.service_area),
                ("Contact details", form.contact),
                ("Social links", form.socials),
            ),
            "do NOT invent an address, phone number, hours, or service area.",
        ),
        _fact_block(
            "VOICE",
            (("Tone", form.tone), ("Aesthetic notes", form.aesthetic)),
            "choose a tone that fits the industry and audience above.",
        ),
        _fact_block(
            "ADDITIONAL CONTEXT",
            (("Description", form.description), ("Notes / must-haves", form.notes)),
            "none given.",
        ),
    )
    return "\n\n".join(sections)
