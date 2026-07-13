"""Prompt-safe tokenization of embedded image data URLs."""

import re

DATA_URI_PATTERN = re.compile(r"data:[\w/.+-]+;base64,[A-Za-z0-9+/=]+")


class ImageRegistry:
    """Replace repeated data URLs with stable short tokens and restore them."""

    def __init__(self) -> None:
        self._source_to_token: dict[str, str] = {}
        self._token_to_source: dict[str, str] = {}

    def compress(self, text: str) -> str:
        if not text:
            return text

        def replacement(match: re.Match[str]) -> str:
            source = match.group(0)
            token = self._source_to_token.get(source)
            if token is None:
                token = f"__IMG_REF_{len(self._source_to_token) + 1}__"
                self._source_to_token[source] = token
                self._token_to_source[token] = source
            return token

        return DATA_URI_PATTERN.sub(replacement, text)

    def resolve(self, text: str) -> str:
        if not text:
            return text
        resolved = text
        for token, source in self._token_to_source.items():
            resolved = resolved.replace(token, source)
        return resolved
