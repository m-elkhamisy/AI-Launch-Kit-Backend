"""Inject document metadata and graceful animation fallback behavior."""

import re
from typing import Final

AOS_FAILSAFE: Final = (
    "<script>window.addEventListener('load',function(){setTimeout(function(){"
    "document.querySelectorAll('[data-aos]').forEach(function(el){"
    "var cs=getComputedStyle(el);if(cs.opacity==='0'||cs.visibility==='hidden'){"
    "el.style.opacity='1';el.style.transform='none';el.style.visibility='visible';}});"
    "},1500);});</script>"
)

_FAVICON: Final = re.compile(r"rel=[\"']icon[\"']", re.IGNORECASE)
_HEAD_CLOSE: Final = re.compile(r"</head>", re.IGNORECASE)


def inject_aos_failsafe(html: str) -> str:
    """Reveal AOS-managed content if the animation library fails to initialize."""

    if "</body>" in html:
        return html.replace("</body>", f"{AOS_FAILSAFE}\n</body>", 1)
    return html + AOS_FAILSAFE


def inject_favicon(html: str, href: str) -> str:
    """Add a favicon unless the document already declares a standard icon link."""

    if _FAVICON.search(html):
        return html
    link = f'<link rel="icon" href="{href}">'
    if _HEAD_CLOSE.search(html):
        return _HEAD_CLOSE.sub(lambda _: f"{link}\n</head>", html, count=1)
    return f"{link}\n{html}"
