"""Agent-callable tools layer over the topic-general listening pipeline.

Each ``tool_*`` function takes a plain ``arguments`` dict and returns a
JSON-serializable result, so it can be exposed over MCP (see ``mcp_server``),
called from tests, or driven by any other host. Thin wrappers around the
pipeline modules — no new behavior, just a stable surface.
"""

from __future__ import annotations

from .normalize import assign_evidence_ids, normalize_serp_result
from .query_pack import build_query_pack
from .report import build_indexed_report
from .zyte_search import search_zyte

_DEFAULT_TOPIC = "agentic web"


def tool_build_query_pack(arguments: dict) -> dict:
    queries = build_query_pack(
        arguments.get("topic", _DEFAULT_TOPIC),
        angles=arguments.get("angles"),
        entities=arguments.get("entities"),
        sites=arguments.get("sites"),
        max_queries=arguments.get("max_queries", 24),
    )
    return {"queries": queries, "count": len(queries)}


def tool_search_serp(arguments: dict) -> dict:
    payload = search_zyte(
        arguments["query"],
        domain=arguments.get("domain", "google.com"),
        max_results=arguments.get("max_results", 10),
        mock=arguments.get("mock", False),
    )
    return {
        "organicResults": payload.get("organicResults", []),
        "fetchedAt": payload.get("fetchedAt", ""),
    }


def tool_normalize_evidence(arguments: dict) -> dict:
    topic = arguments.get("topic", _DEFAULT_TOPIC)
    entities = arguments.get("entities") or []
    query = arguments.get("query", "")
    fetched_at = arguments.get("fetched_at", "")
    evidence = [
        normalize_serp_result(raw, query, fetched_at, topic, entities)
        for raw in arguments.get("raw_results", [])
    ]
    evidence = assign_evidence_ids(evidence)
    return {"evidence": evidence, "count": len(evidence)}


def tool_generate_report(arguments: dict) -> dict:
    report = build_indexed_report(
        topic=arguments.get("topic", _DEFAULT_TOPIC),
        entities=arguments.get("entities") or [],
        angles=arguments.get("angles") or [],
        evidence=arguments.get("evidence", []),
        date_range=arguments.get("date_range", ""),
        run_id=arguments.get("run_id", "mcp-run"),
        deltas=arguments.get("deltas"),
    )
    return {"report_markdown": report}


def tool_run_report(arguments: dict) -> dict:
    """Run the full discover → normalize → report pipeline in memory."""
    topic = arguments.get("topic", _DEFAULT_TOPIC)
    entities = arguments.get("entities") or []
    angles = arguments.get("angles") or []
    sites = arguments.get("sites") or []
    mock = arguments.get("mock", False)
    query_limit = arguments.get("query_limit", 8)
    domain = arguments.get("domain", "google.com")
    max_results = arguments.get("max_results", 10)

    queries = build_query_pack(topic, angles=angles, entities=entities, sites=sites)[:query_limit]
    evidence: list[dict] = []
    skipped_queries: list[dict] = []
    for query in queries:
        try:
            payload = search_zyte(query, domain=domain, max_results=max_results, mock=mock)
        except Exception as exc:  # noqa: BLE001 - a flaky query must not kill the report
            skipped_queries.append({"query": query, "error": str(exc)[:200]})
            continue
        fetched_at = payload.get("fetchedAt", "")
        for raw in payload.get("organicResults", []):
            evidence.append(normalize_serp_result(raw, query, fetched_at, topic, entities))
    evidence = assign_evidence_ids(evidence)

    report = build_indexed_report(
        topic=topic,
        entities=entities,
        angles=angles,
        evidence=evidence,
        date_range=arguments.get("date_range", ""),
        run_id=arguments.get("run_id", "mcp-run"),
    )
    return {
        "report_markdown": report,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "queries_used": queries,
        "skipped_queries": skipped_queries,
    }


_TOPIC_PROPS = {
    "topic": {"type": "string"},
    "entities": {"type": "array", "items": {"type": "string"}},
    "angles": {"type": "array", "items": {"type": "string"}},
    "sites": {"type": "array", "items": {"type": "string"}},
}

TOOLS = [
    {
        "name": "build_query_pack",
        "handler": tool_build_query_pack,
        "description": "Expand a topic into a SERP query pack (recency + intent modifiers, optional angles/entities/sites).",
        "inputSchema": {"type": "object", "properties": {**_TOPIC_PROPS, "max_queries": {"type": "integer"}}},
    },
    {
        "name": "search_serp",
        "handler": tool_search_serp,
        "description": "Run one Zyte Search API SERP query (set mock=true for deterministic sample data).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "domain": {"type": "string"},
                "max_results": {"type": "integer"},
                "mock": {"type": "boolean"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "normalize_evidence",
        "handler": tool_normalize_evidence,
        "description": "Normalize raw SERP results into classified, topic-neutral evidence items with IDs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "raw_results": {"type": "array", "items": {"type": "object"}},
                "query": {"type": "string"},
                "fetched_at": {"type": "string"},
                "topic": {"type": "string"},
                "entities": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["raw_results"],
        },
    },
    {
        "name": "generate_report",
        "handler": tool_generate_report,
        "description": "Render the indexed Markdown research brief from a list of evidence items.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "evidence": {"type": "array", "items": {"type": "object"}},
                **_TOPIC_PROPS,
                "date_range": {"type": "string"},
                "run_id": {"type": "string"},
            },
            "required": ["evidence"],
        },
    },
    {
        "name": "run_report",
        "handler": tool_run_report,
        "description": "Run the full pipeline (query pack -> SERP -> normalize -> report) for any topic. Use mock=true for a credential-free demo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                **_TOPIC_PROPS,
                "mock": {"type": "boolean"},
                "query_limit": {"type": "integer"},
                "domain": {"type": "string"},
                "max_results": {"type": "integer"},
            },
        },
    },
]
