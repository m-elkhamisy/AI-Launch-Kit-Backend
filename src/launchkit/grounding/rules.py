"""Shared factual-discipline instructions for generation prompts."""

FACT_DISCIPLINE = """\
FACTUAL DISCIPLINE — this overrides any instinct to make the copy sound more impressive:
- Only state facts that appear in the FACT SHEET below. Never invent: founding
  years, years-in-business, client/customer counts, project counts, revenue,
  team size, award names, certifications, press mentions, or named
  testimonials/reviewers that are not explicitly given.
- Sections marked "NOT PROVIDED" in the fact sheet must not be papered over
  with invented specifics. Instead, for that section:
    (a) omit the specific claim or the section entirely, OR
    (b) write it without a fabricated number/name (e.g. "trusted by clients
        across the region" instead of "trusted by 500+ clients"), OR
    (c) leave a clearly marked placeholder comment, e.g.
        <!-- ADD: a real client testimonial here --> in HTML, or an obvious
        bracketed placeholder in JSX, so a human can fill it in later.
  Never fabricate a plausible-sounding number, date, name, or quote to fill a
  gap — an honest generic sentence is always correct over an invented specific.
- If the fact sheet DOES include real stats, testimonials, certifications, or
  team bios, use them as given — light copy-editing for flow is fine, but
  don't alter a number, a name, or the substance of a quote.
- Contact details (address, phone, email, hours) come only from the fact
  sheet. If a detail isn't listed, use a generic call to action ("Contact us
  for hours") or an obviously-marked placeholder — never invent an address,
  phone number, or opening hours.
- Never name real competing companies or real people who aren't in the fact
  sheet, and never make legal, medical, or financial claims the fact sheet
  doesn't support."""
