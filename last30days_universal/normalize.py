"""Normalize raw SERP results into classified, topic-neutral evidence.

Every raw search hit becomes an evidence dict with a stable shape: an ID, the
source type (where it lives on the web), the entity it's about (if tracked), a
signal type (what *kind* of thing it is), theme tags, a confidence, and a
research-oriented "why it matters" / "recommended action". None of this is
specific to web scraping — the inference is driven by the topic and the result
text, so the same pipeline works for any subject.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .entities import detect_entity

_STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "what", "your", "you",
    "are", "how", "why", "vs", "best", "latest", "news", "guide", "review",
    "about", "into", "out", "new", "a", "an", "of", "to", "in", "on", "is",
    # URL/markup noise that must never read as a theme.
    "https", "http", "www", "com", "org", "net", "html", "deep", "dive", "worth",
}


def _host(url: str) -> str:
    return urlparse(url or "").netloc.lower().removeprefix("www.")


def classify_source_type(url: str) -> str:
    """Where on the web a result lives — independent of topic."""
    host = _host(url)
    path = urlparse(url or "").path.lower()
    if "reddit.com" in host:
        return "community-reddit"
    if "news.ycombinator.com" in host or "ycombinator.com" in host:
        return "community-hn"
    if "stackoverflow.com" in host or "stackexchange.com" in host:
        return "community-stackoverflow"
    if "github.com" in host:
        return "code-github"
    if "youtube.com" in host or "youtu.be" in host:
        return "video-youtube"
    if "x.com" in host or "twitter.com" in host:
        return "social-x"
    if "wikipedia.org" in host:
        return "reference-wiki"
    if host.startswith("docs.") or "/docs" in path:
        return "docs"
    if "/blog" in path or host.startswith("blog."):
        return "blog"
    if any(token in host for token in ("news", "techcrunch", "verge", "reuters", "bloomberg")):
        return "news"
    return "web"


def infer_signal_type(source_type: str, text: str) -> str:
    """What *kind* of thing this is, in research terms."""
    lower = text.lower()
    if any(word in lower for word in ["launch", "release", "introducing", "announcing", "changelog", "now available"]):
        return "release"
    if " vs " in lower or "alternative" in lower or "compare" in lower or "comparison" in lower:
        return "comparison"
    if any(word in lower for word in ["how to", "tutorial", "guide", "getting started", "example"]):
        return "how-to"
    if source_type.startswith("community"):
        if any(word in lower for word in ["issue", "problem", "can't", "cannot", "blocked", "broken", "bug", "help", "stuck"]):
            return "pain-point"
        return "discussion"
    if source_type == "news":
        return "news"
    if source_type in {"docs", "reference-wiki"}:
        return "reference"
    return "market-move"


def infer_theme_tags(text: str, topic: str) -> list[str]:
    """Derive lightweight theme tags from salient words in the result + topic.

    Topic-neutral by construction: we don't keep a fixed taxonomy, we surface
    the recurring nouns so clustering reflects whatever the subject actually is.
    """
    tags: list[str] = []
    seen: set[str] = set()
    for word in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{3,}", f"{topic} {text}".lower()):
        if word in _STOPWORDS or word in seen:
            continue
        seen.add(word)
        tags.append(word)
        if len(tags) >= 6:
            break
    return tags or ["general"]


def normalize_serp_result(
    raw: dict,
    query: str,
    fetched_at: str,
    topic: str,
    entities: list[str],
) -> dict:
    title = raw.get("title") or "Untitled result"
    url = raw.get("url") or ""
    snippet = raw.get("snippet") or ""
    combined = " ".join([title, url, snippet, query])
    # Themes come from human-readable text only — URLs pollute the tags.
    theme_text = " ".join([title, snippet, query])
    entity = detect_entity(title, url, snippet, query, entities)
    source_type = classify_source_type(url)
    signal_type = infer_signal_type(source_type, combined)
    return {
        "evidence_id": "pending",
        "source_type": source_type,
        "entity": entity,
        "query": query,
        "serp_rank": raw.get("rank"),
        "title": title,
        "url": url,
        "displayed_url": raw.get("displayedUrl") or _host(url),
        "snippet": snippet,
        "quote": snippet,
        "published_at": raw.get("publishedAt") or "",
        "fetched_at": fetched_at,
        "date_confidence": "medium" if fetched_at else "low",
        "theme_tags": infer_theme_tags(theme_text, topic),
        "signal_type": signal_type,
        "confidence": "medium" if source_type != "web" else "low",
        "why_it_matters": build_why_it_matters(entity, source_type, signal_type, title),
        "recommended_action": build_recommended_action(entity, source_type, signal_type),
    }


def assign_evidence_ids(items: list[dict]) -> list[dict]:
    for index, item in enumerate(items, start=1):
        item["evidence_id"] = f"E{index:03d}"
    return items


def build_why_it_matters(entity: str, source_type: str, signal_type: str, title: str) -> str:
    if entity and entity != "None":
        return f"{entity} is visible in this topic's landscape: {title}."
    if signal_type == "pain-point":
        return "Community language here may reveal recurring problems, unmet needs, or comparison criteria."
    if signal_type == "release":
        return "A new release/announcement — likely the freshest movement in the window."
    if source_type.startswith("community"):
        return "Community discussion reflects what practitioners are actually asking and arguing about."
    return "SERP-visible evidence shapes what people discover when researching this topic."


def build_recommended_action(entity: str, source_type: str, signal_type: str) -> str:
    if signal_type == "release":
        return "Summarize what shipped and decide whether it changes your current view."
    if signal_type == "comparison":
        return "Extract the comparison criteria; note which options win and why."
    if signal_type == "pain-point":
        return "Capture the exact phrasing of the problem — it's a real demand signal."
    if entity and entity != "None":
        return f"Track {entity}'s positioning and add it to the entity index."
    if source_type.startswith("community"):
        return "Read the thread for primary-source quotes worth citing."
    return "Skim for relevance and cite if it informs the brief."
