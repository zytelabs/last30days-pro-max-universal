"""Direct community-signal connectors.

SERP discovery under-represents community discussion. These connectors return
results in the same shape as ``zyte_search.search_zyte`` (a payload with
``organicResults`` of ``{rank, title, url, snippet, displayedUrl}``) so they
flow through the normalize pipeline unchanged.

* **Hacker News** via the public Algolia API (no auth) — and it supports a real
  freshness window, giving ``--days`` actual teeth.
* **Reddit** discovered via a Zyte ``site:reddit.com`` SERP query (Reddit's own
  endpoints ban unauthenticated bots), so it stays Zyte-native, no Reddit key.

Both are topic-general: pass any query.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request

from .zyte_search import USER_AGENT, search_zyte, utc_now

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def _mock_community(query: str, prefix: str, host: str, label: str, max_results: int) -> list[dict]:
    """Deterministic community-style results keyed to the query."""
    display = query.replace('"', "").strip() or "the topic"
    templates = [
        ("Discussion: getting started with {q}", "{pts} points, {cmt} comments. Practitioners share first-hand experience with {q}."),
        ("Is {q} actually worth it?", "{pts} points, {cmt} comments. Debate over tradeoffs, alternatives, and gotchas around {q}."),
        ("Problems I hit using {q}", "{pts} points, {cmt} comments. Pain points, bugs, and workarounds for {q}."),
    ]
    results = []
    for rank, (title_t, snippet_t) in enumerate(templates[: max(1, min(max_results, len(templates)))], start=1):
        digest = hashlib.sha1(f"{prefix}-{query}-{rank}".encode("utf-8")).hexdigest()
        pts = 50 + int(digest[:2], 16)
        cmt = 20 + int(digest[2:4], 16)
        results.append({
            "rank": rank,
            "title": title_t.format(q=display),
            "url": f"https://{host}/{prefix}/{digest[:8]}",
            "snippet": f"{label} · " + snippet_t.format(q=display, pts=pts, cmt=cmt),
            "displayedUrl": host,
        })
    return results


def _hit_to_result(rank: int, hit: dict) -> dict:
    object_id = hit.get("objectID", "")
    title = hit.get("title") or hit.get("story_title") or "Hacker News story"
    points = hit.get("points") or 0
    comments = hit.get("num_comments") or 0
    snippet = f"{points} points, {comments} comments on Hacker News."
    external = hit.get("url")
    if external:
        snippet += f" Links to {external}."
    story_text = (hit.get("story_text") or "").strip()
    if story_text:
        snippet += f" {story_text[:200]}"
    return {
        "rank": rank,
        "title": title,
        "url": f"https://news.ycombinator.com/item?id={object_id}",
        "snippet": snippet,
        "displayedUrl": "news.ycombinator.com",
    }


def search_hn(
    query: str,
    *,
    max_results: int = 10,
    mock: bool = False,
    days: int | None = None,
    timeout: int = 30,
) -> dict:
    """Search Hacker News stories for ``query`` and return SERP-shaped results."""
    if mock:
        return {
            "status": "mock-hn",
            "url": f"{HN_SEARCH_URL}?query={query}",
            "fetchedAt": utc_now(),
            "organicResults": _mock_community(query, "item", "news.ycombinator.com", "Hacker News", max_results),
        }

    params = {"query": query, "tags": "story", "hitsPerPage": max_results}
    if days:
        cutoff = int(time.time()) - days * 86400
        params["numericFilters"] = f"created_at_i>{cutoff}"
    url = f"{HN_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    results = [_hit_to_result(i, hit) for i, hit in enumerate(data.get("hits", []), start=1)]
    return {"status": "ok", "url": url, "fetchedAt": utc_now(), "organicResults": results}


def search_reddit(
    query: str,
    *,
    max_results: int = 10,
    mock: bool = False,
    domain: str = "google.com",
    api_key: str | None = None,
    days: int | None = None,
) -> dict:
    """Discover Reddit threads for ``query`` via Zyte (Zyte-native, no Reddit key).

    Reddit's own endpoints ban bots even through anti-ban tiers, but Google has
    Reddit fully indexed — so we run ``site:reddit.com <query>`` through the Zyte
    Search API and keep the Reddit results. Degrades gracefully on failure.
    """
    if mock:
        return {
            "status": "mock-reddit",
            "url": f"https://www.google.com/search?q=site:reddit.com+{query}",
            "fetchedAt": utc_now(),
            "organicResults": _mock_community(query, "comments", "reddit.com/r/all", "r/all", max_results),
        }

    serp_query = f"site:reddit.com {query}"
    try:
        payload = search_zyte(serp_query, domain=domain, max_results=max_results, api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - optional connector must not crash the run
        return {
            "status": "error",
            "url": serp_query,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "fetchedAt": utc_now(),
            "organicResults": [],
        }

    results = []
    for raw in payload.get("organicResults", []):
        url = raw.get("url") or ""
        if "reddit.com" not in url:
            continue
        results.append({
            "rank": len(results) + 1,
            "title": raw.get("title") or "Reddit thread",
            "url": url,
            "snippet": raw.get("snippet") or "",
            "displayedUrl": raw.get("displayedUrl") or "reddit.com",
        })
    return {
        "status": "ok",
        "url": serp_query,
        "fetchedAt": payload.get("fetchedAt") or utc_now(),
        "organicResults": results,
    }
