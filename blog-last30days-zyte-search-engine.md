# How to research the last 30 days of anything with the Zyte Search API

Pick any fast-moving topic, solid-state batteries, AI coding agents, GLP-1 drugs, passkey adoption, and try to answer a simple question: what actually happened in the last 30 days, and what is the evidence for it? Within a few minutes you are drowning. You have a dozen browser tabs open, half of them are SEO filler, the genuinely useful Reddit thread is three pages deep in Google, and by the time you have skimmed enough to feel informed you have no structured record of what you read or why it mattered. Do this twice for the same topic a month apart and you cannot even tell what changed.

The interesting part is that almost all of that pain is a web-data problem, not a reasoning problem. The reasoning is easy once the evidence is in front of you in a clean, attributed, deduplicated form. Getting fresh search results reliably, at the moment you ask, across a topic you did not anticipate yesterday, is the hard part, and it is exactly the part a search API is built to solve. This post walks through a [small open-source engine](https://github.com/zytelabs/last30days-pro-max-universal) that turns "research the last 30 days of X" into a repeatable, evidence-backed pipeline for any X, with the [Zyte API](https://www.zyte.com/zyte-api/) search capability doing the heavy lifting at the discovery stage.

<!-- IMAGE PLACEHOLDER
Nano Banana prompt: A clean, modern isometric illustration on a 135-degree hero gradient background flowing from deep indigo #1a0a3d through magenta-purple #5a1480 to bright magenta #9b1a8a. The scene shows a single glowing search-API node on the left feeding a horizontal pipeline of four connected glass panels labeled with simple icons: a magnifier (discovery), a funnel (normalization), a grid (taxonomy), and a document (report). Thin white connecting lines with small data particles flow left to right. Professional, developer-focused, slightly editorial, no text labels rendered as words.
Alt text suggestion: A search API node feeding a four-stage research pipeline from discovery to report
Placement: hero
-->

## Why a search API is the turbo-boost

The pattern of summarizing recent public signal is not new. This engine is directly inspired by Matt van Horn's [last30days skill](https://github.com/mvanhorn/last30days-skill), an agent skill that researches a topic by aggregating recent signal across roughly a dozen sources, from Reddit and Hacker News to prediction markets and web search, and it keeps that project's core insight while deliberately swapping the spine. The original reaches its sources through a separate, platform-specific integration for each one, several of which work with no key while others unlock with credentials, whereas this version routes discovery through a single web-data layer, and that is the change that makes it general enough to point at any topic. The tradeoff with any many-connectors design is that every source is its own integration to keep working as platforms change, so the maintenance surface grows with the source list, whereas leaning on one search API keeps that surface to a single reliable call.

A single reliable web-data layer collapses that maintenance surface to almost nothing. Google has already indexed the blog posts, the documentation, the news, the Hacker News threads, and the Reddit discussions you care about, so one well-formed search query reaches all of them at once. When that query runs through the Zyte API search capability, the anti-bot handling, retries, and result parsing that normally make automated search a project in itself are simply handled for you, which means the code you write is about research logic rather than plumbing. This is the same idea behind [building robust agentic AI workflows with rapid web data](https://www.zyte.com/blog/building-robust-agentic-ai-workflows-with-rapid-web-data): the fresher and more reliable the data layer, the less your application has to babysit it.

The engine below is stdlib-only Python with one external dependency that matters, the search API, and it ships with a deterministic mock mode so you can run the whole thing end to end before you ever touch a key.

## What the search endpoint gives you that raw search does not

Querying a search engine yourself looks trivial until you do it at any volume, at which point the gap between a script that works on your laptop and one that keeps working in production turns out to be exactly the set of problems the [Zyte API](https://www.zyte.com/zyte-api/) search capability solves for you. A handful of its properties matter most for a research pipeline.

The first is getting blocked. Automated search traffic is precisely the kind of pattern that triggers bans and CAPTCHAs, and handling that yourself means assembling and rotating a fleet of proxies and babysitting them as targets adapt. The search endpoint puts that behind a single call: [automatic unblocking](https://www.zyte.com/zyte-api/unblocking/), with proxy rotation and residential proxies managed for you, so a query that runs once runs the hundredth time too. That reliability is the whole foundation of a listening engine, because a pipeline that silently fails on the third query of a run produces a brief that is quietly wrong.

The second is shape. A raw request hands you an HTML page that you then have to parse, and re-parse every time the markup shifts. The search endpoint returns structured organic results, titles, URLs, snippets, and ranks, as data your code can consume directly, which is why the normalization stage earlier in this post can be a few lines rather than a fragile scraper.

The third is location. What is happening with a topic is often not the same everywhere, and search results differ by market, so the endpoint's geolocation support lets you request results as they actually appear in a given location rather than wherever your server happens to sit. For a topic like regulation, pricing, or product availability, that difference is the story rather than a footnote.

The fourth is that discovery and extraction live behind one key. The same Zyte API that runs the search also fetches and parses the underlying pages through its [AI extraction](https://www.zyte.com/zyte-api/ai-extraction/) capability, so the handoff from "found a promising URL" to "pulled a quotable passage from it" is one credential, one bill, and one mental model rather than two integrations bolted together. You can preview both the results and the cost of a call in the Zyte API Playground before you wire anything up, which takes most of the guesswork out of the first hour.

The fifth, and the one developers tend to underestimate, is explicit control over volume. Each search request takes a `maxResults` value of 10, 20, and so on up to 100 organic results, with the request weight scaling predictably as `max(1, maxResults / 10)`, so you decide per run how deep each query goes and you know the cost of that choice before you send it. A single call will not return 100,000 rows, because a search results page does not hold that many, and leaning into that constraint rather than fighting it is what makes the engine scale: you reach a topic by breadth instead of by one enormous query, fanning the pack out across recency, intent, angles, and entities so that a run of two dozen queries at 100 results each sweeps the landscape far more thoroughly than any single deep request could. Reach on the open web comes from asking many sharp questions, not one broad one, and a results limit you can set per query, priced by a weight you can predict, is exactly the control that lets you tune that tradeoff run by run.

Put together, these turn search from a thing you maintain into a thing you call, and that shift is what lets the rest of the engine stay small.

## From a topic to a query pack

You cannot answer "what happened with X" with a single query for "X". You need breadth across what is new and across the different kinds of pages that carry signal, so the first stage expands a bare topic into a compact, deduplicated query pack. Recency modifiers surface movement in the window, intent modifiers surface different document types, and optional angles, entities, and site filters let you steer.

```python
from last30days_universal.query_pack import build_query_pack

queries = build_query_pack(
    "electric vehicle batteries",
    entities=["Tesla", "CATL", "QuantumScape"],
    angles=["solid state", "recycling"],
)
# '"electric vehicle batteries"'
# '"electric vehicle batteries" latest'
# '"electric vehicle batteries" release'
# '"electric vehicle batteries" alternatives'
# '"electric vehicle batteries" "solid state"'
# '"Tesla" "electric vehicle batteries"'
# '"Tesla" vs "CATL"'
# ... deduplicated and capped
```

The ordering is deliberate. The bare topic and its recency variants carry the freshest signal, so they come first, which means that capping the pack for a cheap spike still keeps the highest-value queries. Nothing here is specific to any subject: the only domain knowledge in the entire engine is what you pass on the command line.

## Discovery: let the search API do the hard part

Each query becomes one search call. In live mode that is a request to the Zyte API search endpoint, authenticated with your [API key](https://app.zyte.com/account/signup/zyteapi) and returning structured organic results. The client handles the parts that usually derail a weekend project: 5xx responses are retried with backoff, permanent client errors fail fast instead of looping, and gzip responses are decompressed before parsing.

```python
def search_zyte(query, *, domain, max_results, mock=False):
    if mock:
        return {"status": "mock", "organicResults": _mock_results(query, max_results)}
    valid_max = max(10, min(100, ((max_results + 5) // 10) * 10))
    return zyte_post(
        "search",
        {"domain": domain, "query": query, "include": ["organic"], "maxResults": valid_max},
    )
```

Mock mode is a first-class citizen rather than an afterthought. It synthesizes deterministic results from the query itself, spread across realistic source types, so the demo produces meaningful evidence for any topic without credentials or network access. That property matters more than it sounds: it means your tests are fast and reproducible, and it means a new contributor can run the full pipeline in the first minute.

```bash
python3 -m last30days_universal.cli \
  --topic "electric vehicle batteries" \
  --entities "Tesla,CATL,QuantumScape" \
  --angles "solid state,recycling" \
  --hn --reddit --extract --mock
```

For developer-heavy topics you can add direct community signal. The Hacker News connector uses the public Algolia API, which supports a real freshness window so the day count has actual teeth, and the Reddit connector runs a `site:reddit.com` search through the same Zyte API search call rather than fighting Reddit's bot bans directly. Both return results in the same shape as the main search, so they flow through the rest of the pipeline unchanged.

## Turning results into evidence, not a blob

A pile of search results is not research. The normalization stage converts every raw hit into a classified evidence item with a stable shape, and this is where a vague "summary" becomes something you can audit. Each item records where it lives on the web, which tracked entity it concerns, what kind of signal it is, a few theme tags, a confidence level, and a plain-language note on why it matters and what to do about it.

```json
{
  "evidence_id": "E091",
  "source_type": "blog",
  "entity": "Tesla",
  "signal_type": "how-to",
  "title": "Deep dive: Tesla electric vehicle batteries",
  "url": "https://blog.example.com/tesla-electric-vehicle-batteries",
  "theme_tags": ["electric", "vehicle", "batteries", "solid", "state"],
  "confidence": "medium",
  "why_it_matters": "Tesla is visible in this topic's landscape.",
  "recommended_action": "Track Tesla's positioning and add it to the entity index."
}
```

Entity attribution is host-first and then relevance-ranked: if a result lives on an entity's own domain that wins outright, and otherwise each tracked entity is scored by where its name appears, weighting a title mention far above a passing snippet mention and breaking ties by earliest position rather than by the order you happened to list things. Theme tags come from human-readable text only, never the URL, so your clusters reflect what the page is actually about. When you want more than a search snippet, the optional extraction step fetches the top-ranked pages through the Zyte API and pulls a longer page-level quote you can cite, which is the same [AI extraction](https://www.zyte.com/zyte-api/ai-extraction/) capability applied to a research context rather than a commerce one.

## The output: an indexed brief with evidence IDs

The point of all this structure is the final artifact. The report stage renders a 12-section markdown brief where every observation links back to an evidence ID, so nothing in the executive summary is a claim you cannot trace to a specific source in the evidence index. A single run writes a small pack of inspectable files: the brief itself, the evidence as both JSONL and CSV, the exact queries used, the raw search payloads, and a run metadata file.

<!-- IMAGE PLACEHOLDER
Nano Banana prompt: A clean editorial diagram on a dark navy #0a0d2e background with bright purple #7c1fa0 accent lines. On the left, a single document icon labeled as a brief; radiating from it, thin purple connector lines link to six small file-card shapes representing brief.md, evidence.jsonl, evidence.csv, queries_used.json, raw_serp_results.json, and run_metadata.json. Minimal, technical, no rendered word-text, generous negative space.
Alt text suggestion: One research run producing six inspectable artifact files
Placement: inline
-->

Because the brief is plain markdown with stable evidence IDs, it is just as readable to a person skimming it as it is to a model summarizing it. That dual-audience property is the quiet payoff of doing the structuring work up front instead of asking an LLM to improvise a summary from raw HTML.

## Watching what changes

Researching a topic once is useful. Researching it repeatedly and seeing the delta is where this stops being a search wrapper and starts being a listening engine. Every run persists its evidence to a local SQLite database keyed by topic, and the next run on the same topic diffs against the most recent prior run, labeling each result as new, recurring, fading, or rank-changed. The "what changed in the window" section of the brief is built from that diff, so the second time you run it you are reading movement rather than a fresh baseline. This is the difference between a one-off lookup and the kind of standing awareness described in [I built scraping agents for 30 days](https://www.zyte.com/blog/i-built-scraping-agents-for-30-days-heres-what-i-learned), where the value compounds because the system remembers what it saw last time.

## Hand it to an agent

The whole pipeline is also exposed as a small Model Context Protocol server, implemented with the standard library and no SDK dependency, so an agent can drive it as a set of tools rather than as a command-line app. The five tools mirror the stages, from building a query pack to running the full report, and `run_report` will execute discovery, normalization, and rendering in a single call.

```json
{
  "method": "tools/call",
  "params": {
    "name": "run_report",
    "arguments": {"topic": "AI coding agents", "entities": ["Cursor", "Copilot"], "mock": true}
  }
}
```

If you want to go deeper on that pattern, the walkthrough on [building your own MCP server with Zyte API](https://www.zyte.com/blog/build-your-own-mcp-server) covers the same approach applied to general web data, and the engine here is essentially that idea pointed at research instead of extraction.

## Try it yourself

The core lesson is that good research is mostly a function of good, fresh, reliable evidence, and that the moment you stop treating discovery as a hand-crafted scraping problem and start treating it as a single search call, the rest of the pipeline gets dramatically simpler. The same handful of commands research electric vehicle batteries, AI coding agents, weight-loss drugs, or whatever lands on your desk tomorrow, because nothing in the engine is specific to any of them.

[Clone the engine](https://github.com/zytelabs/last30days-pro-max-universal), run it in mock mode to see the full brief in under a minute, then drop in a [Zyte API key](https://app.zyte.com/account/signup/zyteapi) and point it at a topic you actually care about. You can read the [Zyte API documentation](https://docs.zyte.com/) to go further with the search and extraction capabilities, and from there the only limit on what you can put under standing, evidence-backed observation is the list of topics you can think of.
