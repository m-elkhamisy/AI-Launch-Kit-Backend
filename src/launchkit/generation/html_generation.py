"""HTML generation completeness checks and one source-compatible retry."""

import re

from launchkit.adapters.openrouter import strip_code_fence
from launchkit.generation.contracts import TextGenerator

DEFAULT_MIN_CHARS = 1_200
HTML_MAX_TOKENS = 32_000


def html_looks_complete(html: str, min_chars: int = DEFAULT_MIN_CHARS) -> bool:
    trimmed = html.strip()
    return bool(
        len(trimmed) >= min_chars
        and re.match(r"^<!DOCTYPE", trimmed, flags=re.IGNORECASE)
        and (
            re.search(r"</html>", trimmed, flags=re.IGNORECASE)
            or re.search(r"</body>", trimmed, flags=re.IGNORECASE)
        )
        and re.search(r"<h[12][\s>]", trimmed, flags=re.IGNORECASE)
    )


class HtmlGenerationService:
    """Generate one complete HTML document, retrying an incomplete first result once."""

    def __init__(self, generator: TextGenerator) -> None:
        self._generator = generator

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = HTML_MAX_TOKENS,
        min_chars: int = DEFAULT_MIN_CHARS,
    ) -> str:
        html = strip_code_fence(await self._generator.generate_text(prompt, max_tokens=max_tokens))
        if html_looks_complete(html, min_chars):
            return html
        retry_prompt = f"""{prompt}

IMPORTANT: your previous attempt was incomplete - it was cut off before the closing </html>
tag, or shipped without a real visible headline/content. Return the COMPLETE single HTML
file, from <!DOCTYPE html> to </html>, with a real <h1> headline and real copy, and nothing
else. Trim copy slightly if needed; a shorter complete page beats a longer broken one."""
        return strip_code_fence(
            await self._generator.generate_text(retry_prompt, max_tokens=max_tokens)
        )
