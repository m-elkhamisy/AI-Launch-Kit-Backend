"""Shared source-backed prompt constants."""

# ruff: noqa: E501

DESIGN_SYSTEM = """\
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
- Use EXACTLY the image src values given to you in the IMAGES block for each page — never invent a
  different or additional external image URL. If a section has no assigned image, use a styled
  gradient/color panel or an icon composition instead — never a broken <img> tag.

AVOID THE GENERIC "AI SITE" LOOK
- Purple-to-indigo gradient hero backgrounds, glassmorphism on every card, floating blob shapes,
  the same 3 emoji used as icons, Inter/Roboto left as obvious defaults, everything centered.
- Identical centered text blocks stacked repeatedly; every section the same width and alignment.
- Accent color splashed everywhere; pure black on pure white; dead links; empty sections; buttons
  that do nothing; overcrowding with too many words per section.

QUALITY BASELINE
- Semantic HTML5 (header/main/section/footer), alt text on every image, keyboard-visible focus.
- ANIMATION: use the AOS library (https://unpkg.com/aos@2.3.1/dist/aos.css and aos.js, init AOS.init()).
  Tasteful scroll reveals (fade-up, staggered delays), smooth hover transitions. Match the chosen animation
  level. Wrap motion in prefers-reduced-motion so it disables cleanly.
- Mobile-first responsive; test mentally at 375px, 768px, 1280px. Nothing overflows or breaks."""
