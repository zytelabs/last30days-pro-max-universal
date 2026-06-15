"""Page extraction: fetch top SERP URLs and pull a page-level quote.

After SERP discovery the report can only cite thin search snippets. This layer
fetches the underlying pages via Zyte API's ``/extract`` endpoint (raw
``httpResponseBody``), strips the HTML to text with the stdlib, and returns a
short excerpt richer than the snippet. Mock mode is deterministic so the demo
works without credentials or network.
"""

from __future__ import annotations

import base64
from html.parser import HTMLParser
from urllib.parse import urlparse

from .zyte_search import utc_now, zyte_post

_QUOTE_CHARS = 400
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}


class _TextExtractor(HTMLParser):
    """Collect visible text, skipping script/style/etc. content."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return " ".join(self._chunks)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - malformed HTML should not crash extraction
        pass
    return " ".join(parser.text().split())


def _excerpt(text: str, limit: int = _QUOTE_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut + "…"


def _mock_extract(url: str) -> dict:
    host = urlparse(url).netloc.lower().removeprefix("www.") or url
    quote = (
        f"[mock extract] Page at {host} expands on the SERP snippet with "
        f"page-level detail — the kind of primary-source quote you'd cite in a brief."
    )
    return {
        "url": url,
        "status": "mock",
        "quote": quote,
        "char_count": len(quote),
        "extracted_at": utc_now(),
    }


def extract_pages(
    urls: list[str],
    *,
    mock: bool = False,
    api_key: str | None = None,
    retries: int = 3,
    backoff: float = 2.0,
) -> list[dict]:
    """Extract a page-level quote for each unique URL (order preserved)."""
    results: list[dict] = []
    seen: set[str] = set()
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        if mock:
            results.append(_mock_extract(url))
            continue
        try:
            data = zyte_post(
                "extract",
                {"url": url, "httpResponseBody": True},
                api_key=api_key,
                retries=retries,
                backoff=backoff,
            )
            encoded = data.get("httpResponseBody", "") or ""
            html = base64.b64decode(encoded).decode("utf-8", "ignore") if encoded else ""
            text = html_to_text(html)
            results.append({
                "url": url,
                "status": "ok",
                "quote": _excerpt(text),
                "char_count": len(text),
                "extracted_at": utc_now(),
            })
        except Exception as exc:  # noqa: BLE001 - one bad page must not kill the run
            results.append({
                "url": url,
                "status": "error",
                "quote": "",
                "error": str(exc)[:200],
                "extracted_at": utc_now(),
            })
    return results
