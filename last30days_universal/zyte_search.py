"""Zyte Search API client with a deterministic, topic-general mock mode.

Live mode posts to ``https://api.zyte.com/v1/search`` (Basic auth via
``ZYTE_API_KEY``) and returns organic SERP results. Mock mode synthesizes
deterministic results *from the query itself*, so the demo produces sensible
evidence for any topic — not a fixed set of scraping vendors — without
credentials or network.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER_AGENT = "last30days-universal/0.1"

# Templates spread mock results across realistic source types so classification,
# theming, and the community sections all have something to chew on.
_MOCK_TEMPLATES = [
    ("https://blog.example.com/{slug}", "blog.example.com",
     "Deep dive: {q}", "A practitioner blog post exploring {q} with concrete examples and tradeoffs."),
    ("https://www.reddit.com/r/all/comments/{hid}/{slug}/", "reddit.com/r/all",
     "Discussion: is {q} worth it?", "Reddit thread weighing pros and cons of {q}; lots of first-hand takes and complaints."),
    ("https://news.ycombinator.com/item?id={num}", "news.ycombinator.com",
     "Show HN: a project about {q}", "Hacker News discussion where developers debate {q} and link to source."),
    ("https://docs.example.org/{slug}", "docs.example.org",
     "{q}: official documentation", "Reference docs covering {q}, setup, and common patterns."),
    ("https://www.technews.com/{slug}", "technews.com",
     "Announcing new updates around {q}", "News roundup covering recent releases and launches related to {q} this month."),
    ("https://github.com/example/{slug}", "github.com",
     "example/{slug}: open-source take on {q}", "GitHub repo implementing {q}; recent releases, stars, and issues."),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "result"


def _mock_results(query: str, max_results: int) -> list[dict]:
    """Deterministic per-query results so any topic yields a meaningful demo."""
    display = query.replace('"', "").strip() or "the topic"
    slug = _slug(display)
    count = max(1, min(max_results, len(_MOCK_TEMPLATES)))
    results = []
    for rank, (url_t, displayed, title_t, snippet_t) in enumerate(_MOCK_TEMPLATES[:count], start=1):
        digest = hashlib.sha1(f"{query}-{rank}".encode("utf-8")).hexdigest()
        url = url_t.format(slug=slug, hid=digest[:6], num=int(digest[:6], 16))
        results.append({
            "rank": rank,
            "title": title_t.format(q=display, slug=slug),
            "url": url,
            "snippet": snippet_t.format(q=display),
            "displayedUrl": displayed,
        })
    return results


def search_zyte(
    query: str,
    *,
    domain: str,
    max_results: int,
    api_key: str | None = None,
    mock: bool = False,
    retries: int = 3,
    backoff: float = 2.0,
) -> dict:
    """Call Zyte Search API, or return deterministic mock data.

    The live SERP endpoint intermittently returns HTTP 500 and is slow, so
    transient 5xx/timeout failures are retried; permanent 4xx errors fail fast.
    """
    if mock:
        return {
            "status": "mock",
            "url": f"https://{domain}/search?q={query}",
            "fetchedAt": utc_now(),
            "organicResults": _mock_results(query, max_results),
        }

    # Zyte requires maxResults to be a multiple of 10 within [10, 100].
    valid_max = max(10, min(100, ((max_results + 5) // 10) * 10))
    return zyte_post(
        "search",
        {"domain": domain, "query": query, "include": ["organic"], "maxResults": valid_max},
        api_key=api_key,
        retries=retries,
        backoff=backoff,
    )


def zyte_post(
    path: str,
    payload: dict,
    *,
    api_key: str | None = None,
    retries: int = 3,
    backoff: float = 2.0,
) -> dict:
    """POST ``payload`` to ``https://api.zyte.com/v1/{path}`` and parse the JSON.

    Shared by the Search (``search``) and extraction (``extract``) endpoints.
    Handles Basic auth, gzip decompression, and retry-on-transient-failure.
    """
    api_key = api_key or os.environ.get("ZYTE_API_KEY")
    if not api_key:
        raise RuntimeError("ZYTE_API_KEY is required unless --mock is used")

    body = json.dumps(payload).encode("utf-8")
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        f"https://api.zyte.com/v1/{path}",
        data=body,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                detail = exc.read().decode("utf-8", "ignore")
                raise RuntimeError(f"Zyte API /{path} failed: HTTP {exc.code}: {detail[:500]}") from exc
            last_error = exc  # 5xx is transient — retry.
        except (urllib.error.URLError, socket.timeout) as exc:
            last_error = exc  # network/timeout — retry.
        if attempt < retries - 1:
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"Zyte API /{path} failed after {retries} attempt(s): {last_error}") from last_error
