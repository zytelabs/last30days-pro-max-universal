"""Topic-general SERP query pack.

The competitor-specific version of this engine built queries around a fixed list
of named competitors. The universal version takes an arbitrary ``topic`` and
expands it into a compact, high-signal query pack using:

* recency modifiers — surface what's *new* in the window (``latest``, ``news``,
  ``release``, a year, ``this month``);
* intent modifiers — surface different *kinds* of pages (``guide``, ``review``,
  ``alternatives``, ``vs``, ``examples``);
* optional angles — user-supplied sub-topics / facets to drill into;
* optional entities — named things to track (products, people, orgs, repos),
  the general-purpose stand-in for "competitors";
* optional sites — ``site:`` filters to pin specific domains.

The goal is breadth *enough* to map a landscape, not infinite search. The pack
is deduplicated and capped.
"""

from __future__ import annotations

import re

# Surface what changed in the window.
RECENCY_MODIFIERS = ["latest", "news", "update", "release", "roadmap", "this month"]

# Surface different kinds of pages about the same topic.
INTENT_MODIFIERS = ["guide", "tutorial", "review", "alternatives", "best", "examples"]


def slugify(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "topic"


def quote_phrase(phrase: str) -> str:
    """Quote a multi-word phrase so SERP treats it as a unit; pass single words through."""
    cleaned = " ".join((phrase or "").strip().split())
    if not cleaned:
        return ""
    if " " in cleaned:
        return f'"{cleaned}"'
    return cleaned


def build_query_pack(
    topic: str,
    *,
    angles: list[str] | None = None,
    entities: list[str] | None = None,
    sites: list[str] | None = None,
    recency: list[str] | None = None,
    intents: list[str] | None = None,
    year: str | None = None,
    max_queries: int = 24,
) -> list[str]:
    """Expand ``topic`` into a deduplicated, capped SERP query pack.

    Ordering is deliberate: the bare topic and recency variants come first
    (they carry the freshest signal), then intent variants, then angles,
    entities, and site filters. ``--query-limit`` slicing the front therefore
    keeps the highest-value queries.
    """
    angles = angles or []
    entities = entities or []
    sites = sites or []
    recency = recency if recency is not None else RECENCY_MODIFIERS
    intents = intents if intents is not None else INTENT_MODIFIERS

    base = quote_phrase(topic)
    queries: list[str] = []
    if base:
        queries.append(base)
        for modifier in recency:
            queries.append(f"{base} {modifier}")
        if year:
            queries.append(f"{base} {year}")
        for modifier in intents:
            queries.append(f"{base} {modifier}")

    for angle in angles:
        angle_q = quote_phrase(angle)
        if angle_q:
            queries.append(f"{base} {angle_q}".strip())

    for entity in entities:
        entity_q = quote_phrase(entity)
        if not entity_q:
            continue
        queries.append(f"{entity_q} {base}".strip())
        queries.append(f"{entity_q} review")
        queries.append(f"{entity_q} alternatives")

    # Pairwise comparisons between tracked entities (highest-signal first pair).
    for left, right in zip(entities, entities[1:]):
        queries.append(f"{quote_phrase(left)} vs {quote_phrase(right)}")

    for site in sites:
        site = site.strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
        if site:
            queries.append(f"site:{site} {base}".strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        query = query.strip()
        key = query.lower()
        if query and key not in seen:
            deduped.append(query)
            seen.add(key)
    return deduped[:max_queries] if max_queries else deduped
