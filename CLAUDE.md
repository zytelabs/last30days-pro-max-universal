# CLAUDE.md

You are helping build **Last30Days Pro Max Universal**, a topic-general web
listening engine for the agentic web, powered by the Zyte Search API.

## Product intent

This is the general-purpose sibling of Last30Days Pro Max. Where Pro Max is
hard-wired to a fixed web-scraping competitor taxonomy, this version researches
**any** topic. The product question is:

> For a given topic, what has the public web been saying and shipping recently —
> and what's the evidence?

The Zyte Search API is the engine's turbo-boost: one reliable web-data layer
turns "research the last 30 days of X" into a repeatable, evidence-backed
pipeline for any X. The output is a full indexed report with evidence IDs, not a
loose summary.

## Shape

```text
fresh SERP discovery → evidence normalization → theme/entity taxonomy → indexed report → action list
```

## Development rules

- Keep nothing topic-specific in the pipeline. The only "domain knowledge" is
  what the user passes via `--topic`, `--entities`, `--angles`, `--sites`.
- Do not reintroduce a hardcoded competitor/vendor registry. Entities are
  always user-supplied and detected by name only (`entities.py`).
- Keep V1 small and useful.
- Use TDD for new behavior: write failing tests first, then implementation.
- Keep the package stdlib-only unless a dependency clearly pays for itself.
- Preserve deterministic `--mock` mode so the demo works without credentials.
- `--mock` must stay topic-general: it synthesizes results from the query, never
  a fixed sample.
- Use `python3 -m unittest discover -s tests -v` as the baseline test command.
- Avoid adding UI, scheduler, multi-agent orchestration, or credentialed social
  APIs in V1.

## Definition of done for a change

- Tests pass.
- Mock mode still generates a report for a non-trivial, non-scraping topic.
- Report includes evidence IDs.
- Generated artifacts remain inspectable:
  - `brief.md`
  - `evidence.csv`
  - `evidence.jsonl`
  - `queries_used.json`
  - `raw_serp_results.json`
  - `run_metadata.json`

## Relationship to the sibling repo

Inspired by `mvanhorn/last30days-skill` and forked in spirit from Last30Days Pro
Max. Do not clone either source-for-source; this repo's job is to prove the
Zyte Search API as a general research substrate, not to rebuild a competitor
tracker.
