# Agentic Search

A production-quality pipeline that accepts a topic query, searches the web, scrapes the top results, and uses an LLM to extract structured, source-traceable entities — returned as clean JSON.

---

## Quickstart

```bash
# 1. Clone / unzip the project
cd agentic_search

# 2. Install dependencies (Python 3.11+ recommended)
pip install -r requirements.txt

# 3. Set API keys
export OPENAI_API_KEY="sk-..."
export BRAVE_API_KEY="..."          # or SERPAPI_KEY if using SerpAPI
export SEARCH_PROVIDER="brave"      # "brave" | "serpapi"

# 4. Run
python main.py "AI startups in healthcare"

# Save output to a file
python main.py "climate tech companies" --output results.json --num-results 10

# Disable cache (e.g. for fresh runs)
python main.py "quantum computing startups" --no-cache
```

---

## Optional: FastAPI Server

```bash
pip install fastapi uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000

# Query
curl -X POST http://localhost:8000/search \
     -H "Content-Type: application/json" \
     -d '{"query": "AI startups in healthcare", "num_results": 5}'
```

---

## Configuration

All settings live in `config.py` and are overridable via environment variables:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required |
| `BRAVE_API_KEY` | — | Required if `SEARCH_PROVIDER=brave` |
| `SERPAPI_KEY` | — | Required if `SEARCH_PROVIDER=serpapi` |
| `SEARCH_PROVIDER` | `brave` | `brave` or `serpapi` |

To change tuneable parameters (max pages, LLM model, dedup threshold), edit the dataclass fields in `config.py` directly.

---

## Output Format

```json
[
  {
    "name": "Flatiron Health",
    "category": "startup",
    "description": "Oncology-focused health tech company...",
    "website": "https://flatiron.com",
    "attributes": {
      "founded_year": 2012,
      "headquarters": "New York, NY",
      "funding": "$175M"
    },
    "sources": [
      {
        "url": "https://example.com/article",
        "evidence": "Flatiron Health raised $175M to expand its cancer data platform..."
      }
    ]
  }
]
```

Each entity includes one or more `sources`, each with:
- `url` — the page it was extracted from
- `evidence` — a verbatim snippet from that page

---

## Architecture

```
main.py          Orchestrates the pipeline; CLI entry point
config.py        All settings in one place (env vars + defaults)
search.py        Web search abstraction (Brave / SerpAPI)
scraper.py       Async concurrent page fetching + HTML cleaning
extractor.py     OpenAI-based structured entity extraction
aggregator.py    Fuzzy deduplication and entity merging
schema.py        Pydantic models: Entity, Source, ExtractionResult
api.py           (bonus) FastAPI REST endpoint
```

### Data flow

```
Query
  │
  ▼
search.py ──► top N URLs
  │
  ▼
scraper.py ──► cleaned page text (async, cached)
  │
  ▼
extractor.py ──► raw Entity list per page (via OpenAI)
  │
  ▼
aggregator.py ──► deduplicated, merged Entity list
  │
  ▼
JSON output
```

---

## Design Trade-offs

### Why per-page extraction?
Sending all page content to one prompt would exceed context limits and make attribution harder. Per-page extraction keeps prompts short, costs predictable, and makes it trivial to parallelise later.

### Why fuzzy name matching vs embeddings?
`rapidfuzz.token_sort_ratio` covers the vast majority of real duplicate cases (word-order variants, minor typos) at zero API cost and with deterministic behaviour. Embedding-based dedup would be more semantically powerful but adds latency, cost, and an extra API dependency. At the scale of 5–10 pages / 50 entities per run, fuzzy matching is the right call.

### Why `gpt-4o-mini` as default?
It's ~20× cheaper than GPT-4o with only a modest quality drop for extraction tasks. Swapping to `gpt-4o` is a one-line change in `config.py`.

### Why not parallel extraction?
The bottleneck is network I/O (already async in the scraper). LLM calls are fast enough sequentially for ≤10 pages. Adding async extraction would complicate error handling without a meaningful speedup.

### Why file-based caching?
Minimal complexity — no Redis dependency, works offline after the first run, and is easy to inspect. For a production system, Redis or a proper KV store would be preferred.

---

## Limitations

- **Dynamic / JS-rendered pages**: `aiohttp` + BeautifulSoup cannot execute JavaScript. Sites like React SPAs will return sparse content. A Playwright-based scraper would fix this.
- **Paywalled content**: Paywalled pages return preview text only.
- **LLM hallucination**: The prompt instructs the model to stay grounded, and `evidence_text` provides a check — but the model can still occasionally fabricate. Manual spot-checking is recommended for high-stakes use.
- **Rate limits**: Heavy use (>50 queries/hour) may hit OpenAI or search API rate limits. The retry logic handles transient issues, but sustained load requires a queue.
- **Dedup precision**: Fuzzy string matching works well for company names but may over-merge similar-sounding entities (e.g. two different startups with similar names in the same space).
