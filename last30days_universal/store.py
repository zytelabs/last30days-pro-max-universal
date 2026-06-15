"""SQLite persistence for run-over-run deltas.

Each run's evidence is stored so the report's "What Changed in the Window"
section can compare the current run against the most recent prior run on the
same topic and label evidence as new, recurring, fading, or rank-changed.
Identity across runs is the result URL. Uses the stdlib ``sqlite3`` only.
"""

from __future__ import annotations

import hashlib
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    topic TEXT,
    created_at TEXT,
    days INTEGER
);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT,
    run_id TEXT,
    url TEXT,
    query TEXT,
    title TEXT,
    snippet TEXT,
    entity TEXT,
    source_type TEXT,
    serp_rank INTEGER,
    content_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence(run_id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def content_hash(title: str, snippet: str) -> str:
    return hashlib.sha1(f"{title}\n{snippet}".encode("utf-8")).hexdigest()


def save_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    topic: str,
    created_at: str,
    days: int,
    evidence: list[dict],
) -> None:
    """Persist a run and its evidence; re-running the same run_id replaces it."""
    conn.execute(
        "INSERT OR REPLACE INTO runs(run_id, topic, created_at, days) VALUES (?, ?, ?, ?)",
        (run_id, topic, created_at, days),
    )
    conn.execute("DELETE FROM evidence WHERE run_id = ?", (run_id,))
    conn.executemany(
        """INSERT INTO evidence(
            evidence_id, run_id, url, query, title, snippet,
            entity, source_type, serp_rank, content_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                item.get("evidence_id"),
                run_id,
                item.get("url"),
                item.get("query"),
                item.get("title"),
                item.get("snippet"),
                item.get("entity"),
                item.get("source_type"),
                item.get("serp_rank"),
                content_hash(item.get("title", "") or "", item.get("snippet", "") or ""),
            )
            for item in evidence
        ],
    )
    conn.commit()


def _latest_prior_run(conn: sqlite3.Connection, topic: str, exclude_run_id: str):
    return conn.execute(
        """SELECT run_id, created_at FROM runs
           WHERE topic = ? AND run_id != ?
           ORDER BY created_at DESC, rowid DESC LIMIT 1""",
        (topic, exclude_run_id),
    ).fetchone()


def _evidence_by_url(conn: sqlite3.Connection, run_id: str) -> dict:
    rows = conn.execute(
        "SELECT url, title, serp_rank FROM evidence WHERE run_id = ?", (run_id,)
    ).fetchall()
    return {row["url"]: row for row in rows if row["url"]}


def _empty_deltas() -> dict:
    return {
        "previous_run_id": None,
        "previous_created_at": None,
        "new": [],
        "recurring": [],
        "fading": [],
        "rank_changed": [],
    }


def compute_deltas(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    topic: str,
    evidence: list[dict],
) -> dict:
    """Compare current evidence to the latest prior run on the same topic.

    Must be called BEFORE ``save_run`` for the current run.
    """
    prior = _latest_prior_run(conn, topic, run_id)
    if prior is None:
        return _empty_deltas()

    prior_map = _evidence_by_url(conn, prior["run_id"])

    current_map: dict[str, dict] = {}
    for item in evidence:
        url = item.get("url")
        if not url:
            continue
        existing = current_map.get(url)
        if existing is None or _rank(item) < _rank(existing):
            current_map[url] = item

    new, recurring, rank_changed = [], [], []
    for url, item in current_map.items():
        prior_row = prior_map.get(url)
        if prior_row is None:
            new.append(item)
            continue
        recurring.append(item)
        old_rank, new_rank = prior_row["serp_rank"], item.get("serp_rank")
        if old_rank is not None and new_rank is not None and old_rank != new_rank:
            rank_changed.append({
                "url": url,
                "title": item.get("title"),
                "old_rank": old_rank,
                "new_rank": new_rank,
            })

    fading = [
        {"url": url, "title": row["title"], "serp_rank": row["serp_rank"]}
        for url, row in prior_map.items()
        if url not in current_map
    ]

    return {
        "previous_run_id": prior["run_id"],
        "previous_created_at": prior["created_at"],
        "new": new,
        "recurring": recurring,
        "fading": fading,
        "rank_changed": rank_changed,
    }


def _rank(item: dict) -> int:
    rank = item.get("serp_rank")
    return rank if isinstance(rank, int) else 9999
