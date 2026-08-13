"""Fetch a public website and reduce its HTML to readable text for AI extraction."""

import ipaddress
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from launchkit.core.exceptions import DomainError

WEBSITE_FETCH_TIMEOUT_SECONDS = 20.0
WEBSITE_MAX_BYTES = 2 * 1024 * 1024
_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}
_SKIPPED_ELEMENTS = {"script", "style", "noscript", "svg", "template", "iframe", "head"}
# Block ends force line breaks so headings and paragraphs stay separated.
_BLOCK_ELEMENTS = {
    "p", "div", "section", "article", "header", "footer", "main", "aside", "nav",
    "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br", "blockquote", "figcaption",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self.title = ""
        self.meta_description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_ELEMENTS:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attributes = dict(attrs)
            name = (attributes.get("name") or attributes.get("property") or "").lower()
            if name in {"description", "og:description"} and not self.meta_description:
                self.meta_description = (attributes.get("content") or "").strip()
        if tag in _BLOCK_ELEMENTS:
            self._chunks.append("\n")
        # Alt text often carries the only description of hero imagery.
        if tag == "img":
            alt = (dict(attrs).get("alt") or "").strip()
            if alt:
                self._chunks.append(f" {alt} ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_ELEMENTS and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK_ELEMENTS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        # The title lives inside <head>, which is otherwise skipped wholesale.
        if self._in_title:
            self.title += data
            return
        if self._skip_depth > 0:
            return
        if data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        lines = "".join(self._chunks).splitlines()
        cleaned = [" ".join(line.split()) for line in lines]
        return "\n".join(line for line in cleaned if line)


def website_page_text(html: str) -> str:
    """Readable text for one HTML page: title, meta description, then body copy."""

    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    parts: list[str] = []
    title = " ".join(parser.title.split())
    if title:
        parts.append(f"Page title: {title}")
    if parser.meta_description:
        parts.append(f"Meta description: {parser.meta_description}")
    body = parser.text()
    if body:
        parts.append(body)
    return "\n\n".join(parts)


def validate_website_url(url: str) -> str:
    """Normalize a user-supplied site URL and reject anything that is not a public web page."""

    candidate = url.strip()
    if not candidate:
        raise DomainError("Enter your website address.")
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise DomainError("The website address must start with http:// or https://.")
    hostname = (parsed.hostname or "").lower()
    if hostname in _BLOCKED_HOSTNAMES:
        raise DomainError("This address points to a private network and cannot be scanned.")
    if not hostname or "." not in hostname:
        # Single-label hosts (intranet names) are not reachable public sites.
        raise DomainError("Enter a full public website address such as https://example.com.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise DomainError("This address points to a private network and cannot be scanned.")
    return candidate


async def fetch_website_html(client: httpx.AsyncClient, url: str) -> str:
    """Download one page of the user's existing website, capped in size and time."""

    try:
        response = await client.get(
            url,
            follow_redirects=True,
            timeout=WEBSITE_FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": "LaunchKitBot/1.0 (+website discovery)"},
        )
    except httpx.HTTPError as exc:
        raise DomainError(
            "The website could not be reached. Check the address and try again."
        ) from exc
    if response.status_code >= 400:
        raise DomainError(
            f"The website responded with an error (HTTP {response.status_code})."
        )
    content_type = response.headers.get("content-type", "").lower()
    if content_type and "html" not in content_type and "text" not in content_type:
        raise DomainError("This address is not a web page, so it cannot be scanned.")
    return response.text[:WEBSITE_MAX_BYTES]
