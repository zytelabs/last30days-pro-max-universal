"""Render an indexed, topic-general research brief from evidence.

Same contract as the competitor engine — every claim links back to an evidence
ID — but the sections describe *any* topic's last-30-days landscape: what
changed, the sources and entities in play, theme clusters, community
discussion, the SERP landscape, a reading list, gaps, and next actions.
"""

from __future__ import annotations

from collections import defaultdict

SECTION_INDEX = [
    "1. Executive Summary",
    "2. What Changed in the Window",
    "3. Top Sources and Domains",
    "4. Entities Tracked",
    "5. Theme Clusters",
    "6. Community and Developer Signal",
    "7. Search / SERP Landscape",
    "8. Key Reading List",
    "9. Open Questions and Gaps",
    "10. Recommended Next Actions",
    "11. Evidence Index",
    "12. Appendix: Queries, Source Coverage, Warnings",
]


def group_by(items: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item.get(key) or "Unknown"].append(item)
    return dict(grouped)


def build_indexed_report(
    *,
    topic: str,
    entities: list[str],
    angles: list[str],
    evidence: list[dict],
    date_range: str,
    run_id: str,
    deltas: dict | None = None,
) -> str:
    by_entity = group_by(evidence, "entity")
    by_source = group_by(evidence, "source_type")
    by_domain = group_by(evidence, "displayed_url")
    by_theme: dict[str, list[dict]] = defaultdict(list)
    for item in evidence:
        for tag in item.get("theme_tags", []):
            by_theme[tag].append(item)

    lines: list[str] = []
    lines.append(f'# Last30Days Pro Max — "{topic}" Research Brief')
    lines.append("")
    lines.append(f"- **Run ID:** `{run_id}`")
    lines.append(f"- **Date range:** {date_range}")
    lines.append(f"- **Topic:** {topic}")
    if angles:
        lines.append(f"- **Angles:** {', '.join(angles)}")
    if [e for e in entities]:
        lines.append(f"- **Entities tracked:** {', '.join(entities)}")
    lines.append(f"- **Evidence items:** {len(evidence)}")
    lines.append("")

    lines.append("## 0. Index")
    lines.extend(f"- [{section}](#{_anchor(section)})" for section in SECTION_INDEX)
    lines.append("")

    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(
        f"This run scans fresh public-web evidence about **{topic}**. Treat it as a "
        "decision aid, not a final truth: every observation links back to an evidence "
        "ID in the Evidence Index."
    )
    lines.append("")
    tracked_seen = [e for e in entities if by_entity.get(e)]
    if tracked_seen:
        lines.append(f"- Tracked entities that surfaced in evidence: {', '.join(tracked_seen)}.")
    top_themes = [t for t, _ in sorted(by_theme.items(), key=lambda p: len(p[1]), reverse=True)][:8]
    lines.append(f"- Strongest recurring themes: {', '.join(top_themes) or 'none yet'}.")
    releases = [i for i in evidence if i.get("signal_type") == "release"]
    if releases:
        lines.append(f"- {len(releases)} release/announcement signal(s) in the window — see §2.")
    lines.append(f"- Sources covered: {', '.join(sorted(by_source)) or 'none'}.")
    lines.append("")

    lines.append("## 2. What Changed in the Window")
    lines.append("")
    _render_changed_section(lines, evidence, deltas)
    lines.append("")

    lines.append("## 3. Top Sources and Domains")
    lines.append("")
    ranked_domains = sorted(by_domain.items(), key=lambda p: len(p[1]), reverse=True)
    for domain, items in ranked_domains[:12]:
        lines.append(f"- **{domain}** — {len(items)} item(s); top: {items[0]['title']}")
    lines.append("")

    lines.append("## 4. Entities Tracked")
    lines.append("")
    if not entities:
        lines.append("- No entities were tracked this run. Pass `--entities` to attribute and compare named things (products, people, orgs).")
    for idx, entity in enumerate(entities, start=1):
        lines.append(f"### 4.{idx} {entity}")
        items = by_entity.get(entity, [])
        if not items:
            lines.append("- No strong evidence surfaced in this run.")
        for item in items[:8]:
            lines.append(f"- **{item['evidence_id']}** [{item['title']}]({item['url']})")
            lines.append(f"  - Signal: {item['signal_type']} · Source: {item['source_type']} · Confidence: {item['confidence']}")
            lines.append(f"  - Why it matters: {item['why_it_matters']}")
            lines.append(f"  - Action: {item['recommended_action']}")
        lines.append("")

    lines.append("## 5. Theme Clusters")
    lines.append("")
    for theme, items in sorted(by_theme.items(), key=lambda pair: len(pair[1]), reverse=True)[:15]:
        ids = ", ".join(item["evidence_id"] for item in items[:8])
        lines.append(f"- **{theme}** — {len(items)} item(s): {ids}")
    lines.append("")

    lines.append("## 6. Community and Developer Signal")
    lines.append("")
    community = [i for i in evidence if i.get("source_type", "").startswith("community")]
    if community:
        for item in community[:12]:
            lines.append(f"- **{item['evidence_id']}** ({item['source_type']}) — {item['snippet']}  ")
            lines.append(f"  Action: {item['recommended_action']}")
    else:
        lines.append("- No community-specific evidence surfaced yet. Add `--hn` / `--reddit` for stronger practitioner signal.")
    lines.append("")

    lines.append("## 7. Search / SERP Landscape")
    lines.append("")
    by_query = group_by(evidence, "query")
    for query, items in list(by_query.items())[:24]:
        lines.append(f"- `{query}` → {len(items)} evidence item(s); top: {items[0]['title']}")
    lines.append("")

    lines.append("## 8. Key Reading List")
    lines.append("")
    # Best-ranked unique URLs make the fastest path into the topic.
    seen_urls: set[str] = set()
    reading = []
    for item in sorted(evidence, key=lambda i: _rank(i)):
        if item["url"] and item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            reading.append(item)
    for item in reading[:10]:
        lines.append(f"- **{item['evidence_id']}** [{item['title']}]({item['url']}) — {item['signal_type']}")
    lines.append("")

    lines.append("## 9. Open Questions and Gaps")
    lines.append("")
    lines.append("- Which claims rest on a single source and need corroboration before you act on them?")
    if not community:
        lines.append("- No primary community voices captured — practitioner pain and language are missing.")
    if not any(i.get("signal_type") == "release" for i in evidence):
        lines.append("- No clear release/announcement detected — either the window is quiet or queries missed it.")
    lines.append("- Which sub-angles produced thin coverage and deserve a follow-up `--angles` run?")
    lines.append("")

    lines.append("## 10. Recommended Next Actions")
    lines.append("")
    unique_actions: list[str] = []
    for item in evidence:
        action = item.get("recommended_action", "")
        if action and action not in unique_actions:
            unique_actions.append(action)
    for action in unique_actions[:8]:
        lines.append(f"- {action}")
    if not unique_actions:
        lines.append("- No evidence yet — widen the query pack or disable `--mock` to run live.")
    lines.append("")

    lines.append("## 11. Evidence Index")
    lines.append("")
    for item in evidence:
        lines.append(f"### {item['evidence_id']} — {item['title']}")
        lines.append(f"- URL: {item['url']}")
        lines.append(f"- Query: `{item['query']}`")
        lines.append(f"- Entity: {item['entity']}")
        lines.append(f"- Source type: {item['source_type']}")
        lines.append(f"- Signal type: {item['signal_type']}")
        lines.append(f"- SERP rank: {item.get('serp_rank', '')}")
        lines.append(f"- Snippet: {item.get('snippet', '')}")
        quote = item.get("quote", "")
        if quote and quote != item.get("snippet", ""):
            lines.append(f"- Quote (extracted): {quote}")
        lines.append(f"- Tags: {', '.join(item.get('theme_tags', []))}")
        lines.append(f"- Why it matters: {item.get('why_it_matters', '')}")
        lines.append(f"- Recommended action: {item.get('recommended_action', '')}")
        lines.append("")

    lines.append("## 12. Appendix: Queries, Source Coverage, Warnings")
    lines.append("")
    if angles:
        lines.append("### Angles")
        for angle in angles:
            lines.append(f"- {angle}")
        lines.append("")
    lines.append("### Source coverage")
    for source, items in sorted(by_source.items()):
        lines.append(f"- {source}: {len(items)}")
    lines.append("")
    lines.append("### Warnings")
    lines.append("- Live Zyte Search API calls are the default (requires `ZYTE_API_KEY`). Pass `--mock` for deterministic sample data.")
    lines.append("- SERP-discovered social results are incomplete; use `--hn` / `--reddit` for stronger community coverage.")
    lines.append("- Historical delta sections require stored previous runs on the same topic.")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_changed_section(lines: list[str], evidence: list[dict], deltas: dict | None) -> None:
    if not deltas or deltas.get("previous_run_id") is None:
        if deltas is not None:
            lines.append("No previous run stored for this topic yet — this run is the baseline. Re-run later to see new / recurring / fading / rank-changed deltas.")
        else:
            lines.append("Historical comparison is disabled for this run (no run store). Run with persistence enabled to diff against the previous run.")
        for item in evidence[:5]:
            lines.append(f"- **{item['evidence_id']}** — {item['title']} ({item.get('entity', 'None')})")
        return

    lines.append(
        f"Compared against previous run `{deltas['previous_run_id']}` "
        f"({deltas.get('previous_created_at', '')})."
    )
    lines.append("")
    lines.append(f"- **New** this run: {len(deltas['new'])}")
    for item in deltas["new"][:8]:
        lines.append(f"  - {item.get('evidence_id', '')} {item.get('title', '')} ({item.get('entity', 'None')})")
    lines.append(f"- **Recurring** (also in previous run): {len(deltas['recurring'])}")
    lines.append(f"- **Fading candidates** (in previous run, absent now): {len(deltas['fading'])}")
    for item in deltas["fading"][:8]:
        lines.append(f"  - {item.get('title', '')} (was rank {item.get('serp_rank', '')})")
    lines.append(f"- **Rank changed**: {len(deltas['rank_changed'])}")
    for change in deltas["rank_changed"][:8]:
        lines.append(f"  - {change.get('title', '')}: rank {change['old_rank']} → {change['new_rank']}")


def _rank(item: dict) -> int:
    rank = item.get("serp_rank")
    return rank if isinstance(rank, int) else 9999


def _anchor(section: str) -> str:
    text = section.lower()
    for ch in (".", "/", ":", ","):
        text = text.replace(ch, "")
    return text.replace(" ", "-")
