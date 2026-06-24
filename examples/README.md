# Examples

Two sample runs, so you can see the difference between a credential-free demo and the real thing.

## `live-ai-coding-agents/` — REAL run ✅

Generated against the live **Zyte Search API** (`mock: false`). Topic: *AI coding agents*, tracking Cursor, Claude Code, and Copilot, with the Hacker News connector on. Every result is a real page discovered through the SERP endpoint — real titles, URLs, and snippets, classified into 69 evidence items across blog, GitHub, Hacker News, Reddit, docs, news, YouTube, and web sources.

```bash
export ZYTE_API_KEY="your-key"
python3 -m last30days_universal.cli --topic "AI coding agents" \
  --entities "Cursor,Claude Code,Copilot" --angles "pricing,benchmarks" --hn
```

Start with [`live-ai-coding-agents/brief.md`](live-ai-coding-agents/brief.md).

## `mock-electric-vehicle-batteries/` — MOCK run (no key) ⚙️

Generated in `--mock` mode (`mock: true`). The results are **deterministic placeholders synthesized from the query** (`blog.example.com`, `docs.example.org`, …), not real pages. Mock mode exists so the full pipeline runs end to end with no key and no network, which keeps the tests fast and the demo reproducible. Use it to understand the artifact shape, not to read real evidence.

```bash
python3 -m last30days_universal.cli --topic "electric vehicle batteries" \
  --entities "Tesla,CATL,QuantumScape" --angles "solid state,recycling" \
  --hn --reddit --extract --mock
```

> The two runs produce the identical artifact set (`brief.md`, `evidence.jsonl`, `evidence.csv`, `queries_used.json`, `raw_serp_results.json`, `run_metadata.json`). The only difference is whether the SERP results are real. Check `run_metadata.json` → `"mock"` to tell them apart.
