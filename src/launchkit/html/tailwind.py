"""Normalize unsupported numeric Tailwind utilities from generated HTML."""

import re
from typing import Final

_VALID_SCALE: Final = (
    0,
    0.5,
    1,
    1.5,
    2,
    2.5,
    3,
    3.5,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    14,
    16,
    20,
    24,
    28,
    32,
    36,
    40,
    44,
    48,
    52,
    56,
    60,
    64,
    72,
    80,
    96,
)
_PREFIXES: Final = (
    "h",
    "w",
    "p",
    "pt",
    "pb",
    "pl",
    "pr",
    "px",
    "py",
    "m",
    "mt",
    "mb",
    "ml",
    "mr",
    "mx",
    "my",
    "gap",
    "gap-x",
    "gap-y",
    "space-x",
    "space-y",
    "top",
    "bottom",
    "left",
    "right",
    "inset",
    "size",
    "min-h",
    "min-w",
    "max-h",
    "max-w",
    "leading",
    "text",
)
_PREFIX_ALTERNATIVES = "|".join(
    sorted((re.escape(prefix) for prefix in _PREFIXES), key=len, reverse=True)
)
_NUMERIC_UTILITY: Final = re.compile(
    rf"((?:[a-z0-9-]+:)*)({_PREFIX_ALTERNATIVES})-(\d+(?:\.\d+)?)\b"
)


def _nearest_scale_value(value: float) -> float:
    return min(_VALID_SCALE, key=lambda candidate: (abs(candidate - value), -candidate))


def fix_tailwind_classes(html: str) -> str:
    """Snap off-scale numeric utilities to the nearest Karim-supported value."""

    def normalize(match: re.Match[str]) -> str:
        variant, prefix, number = match.groups()
        value = float(number)
        if value in _VALID_SCALE or (prefix == "text" and value >= 100):
            return match.group(0)
        snapped = _nearest_scale_value(value)
        rendered = str(int(snapped)) if snapped == int(snapped) else str(snapped)
        return f"{variant}{prefix}-{rendered}"

    return _NUMERIC_UTILITY.sub(normalize, html)
