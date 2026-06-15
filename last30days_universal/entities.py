"""User-driven entity detection.

The competitor-specific engine shipped a hardcoded registry of scraping vendors
with known domains. The universal engine can't assume *which* named things a
topic cares about, so entities are supplied by the caller (``--entities``) and
detected purely by name:

1. host-first — if a result's host contains the entity's slug, attribute it
   there (highest confidence, e.g. ``apify.com`` → ``Apify``);
2. otherwise relevance-ranked — weight each entity by where its name appears
   (title > url > snippet/query), tie-broken by earliest mention, never by the
   order entities were listed in.

No registry, no network: an entity is just a name plus the slug derived from it.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# A title mention says far more about what a result is *about* than a snippet one.
_FIELD_WEIGHTS = (("title", 3), ("url", 2), ("snippet", 1), ("query", 1))


def normalize_host(host: str) -> str:
    return (host or "").lower().removeprefix("www.")


def host_of(url: str) -> str:
    return normalize_host(urlparse(url or "").netloc)


def entity_slug(name: str) -> str:
    """Collapse an entity name to an alphanumeric slug for host matching."""
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def _keywords_for(name: str) -> list[str]:
    """Match the full name and, when multi-word, its collapsed slug too."""
    name = (name or "").strip()
    keywords = []
    if name:
        keywords.append(name.lower())
    slug = entity_slug(name)
    if slug and slug not in keywords:
        keywords.append(slug)
    return keywords


def _matches(text: str, keyword: str) -> bool:
    # Multi-word keywords are matched literally; single tokens on word boundaries.
    if " " in keyword:
        return keyword in text
    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


def _first_position(text: str, keywords: list[str]) -> int:
    best = len(text)
    for keyword in keywords:
        idx = text.find(keyword)
        if idx != -1:
            best = min(best, idx)
    return best


def entity_for_host(host: str, names: list[str]) -> str | None:
    """Return the entity whose slug owns ``host``, if any."""
    host_slug = entity_slug(host)
    if not host_slug:
        return None
    for name in names:
        slug = entity_slug(name)
        # Require a reasonably specific slug to avoid spurious substring hits.
        if len(slug) >= 3 and slug in host_slug:
            return name
    return None


def detect_entity(title: str, url: str, snippet: str, query: str, names: list[str]) -> str:
    """Attribute a SERP result to one of ``names``, or ``"None"``.

    Host ownership wins outright; otherwise entities are relevance-ranked by
    weighted field mentions, tie-broken by earliest mention (never list order).
    """
    if not names:
        return "None"

    host_match = entity_for_host(host_of(url), names)
    if host_match:
        return host_match

    fields = {
        "title": (title or "").lower(),
        "url": (url or "").lower(),
        "snippet": (snippet or "").lower(),
        "query": (query or "").lower(),
    }
    combined = " ".join(fields.values())

    ranked = []
    for name in names:
        keywords = _keywords_for(name)
        score = 0
        for field_name, weight in _FIELD_WEIGHTS:
            if any(_matches(fields[field_name], kw) for kw in keywords):
                score += weight
        if score:
            ranked.append((score, _first_position(combined, keywords), name))

    if not ranked:
        return "None"
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return ranked[0][2]
