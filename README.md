# Agentic Search

A production-quality pipeline that accepts a topic query, searches the web, scrapes the top results, and uses an LLM to extract structured, source-traceable entities — returned as clean JSON with a beautiful web UI.

---

## Live Demo

👉 https://web-production-fd58c.up.railway.app

---

## Quickstart
```bash
# 1. Clone the repo
git clone https://github.com/Sam-1806/AgenticAI-Search.git
cd AgenticAI-Search

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add API keys to .env file
cp .env.example .env
# Edit .env with your keys

# 5. Run CLI
python main.py "AI startups in healthcare"

# Save output to file
python main.py "climate tech companies" --output results.json

# Disable cache
python main.py "quantum computing startups" --no-cache
```

---

## Web UI
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in your browser.

Features:
- Search box with example queries
- Live pipeline status indicator (Search → Scrape → Extract → Aggregate)
- Entity cards with attributes and source evidence
- Confidence scores on each entity
- Toggle between card view and raw JSON
- Download results as JSON

---

## API Keys Required

| Key | Where to get it | Cost |
|---|---|---|
| `GROQ_API_KEY` | https://console.groq.com | Free |
| `SERPAPI_KEY` | https://serpapi.com | 100 free searches/month |

Create a `.env` file in the project root:
```
GROQ_API_KEY=your-groq-key
SERPAPI_KEY=your-serpapi-key
SEARCH_PROVIDER=serpapi
```

---

## Architecture
```
main.py          Orchestrates the pipeline; CLI entry point
config.py        All settings in one place (env vars + defaults)
search.py        Web search abstraction (SerpAPI)
scraper.py       Async concurrent page fetching + HTML cleaning
extractor.py     Groq/Llama-based extraction + reflection pass
aggregator.py    Fuzzy deduplication and entity merging
schema.py        Pydantic models: Entity, Source, ExtractionResult
api.py           FastAPI backend + single-page web UI
```

### Data flow
```
Query
  │
  ▼
search.py ──► top N URLs (SerpAPI)
  │
  ▼
scraper.py ──► cleaned page text (async aiohttp, file-cached)
  │
  ▼
extractor.py ──► raw Entity list per page (Groq / Llama 3.1)
  │
  ▼
aggregator.py ──► deduplicated, merged Entity list (with merge_reason)
  │
  ▼
extractor.py ──► reflection pass (confidence scoring, noise removal)
  │
  ▼
JSON output + Web UI
```

---

## Output Format
```json
[
  {
    "name": "Abridge",
    "category": "startup",
    "description": "Transforms patient-clinician conversations into AI-generated clinical notes.",
    "website": "https://www.abridge.com",
    "attributes": {
      "industry": "healthcare",
      "product": "AI platform for clinical conversations"
    },
    "sources": [
      {
        "url": "https://www.abridge.com/",
        "evidence": "Abridge transforms patient-clinician conversations into contextually aware, clinically useful, and billable AI-generated notes."
      }
    ],
    "confidence": 0.9,
    "merge_reason": null
  }
]
```

---

## Design Trade-offs

### Why per-page extraction?
Sending all page content in one prompt would exceed context limits and make source attribution impossible. Per-page extraction keeps prompts short, costs predictable, and attribution clean.

### Why a reflection pass?
After initial extraction, a second LLM call reviews all entities and removes low-confidence or hallucinated ones, and improves descriptions using only grounded evidence. This significantly improves output quality — in testing, it reduced noise from ~31 raw entities to ~10 high-quality ones. The cost is one extra LLM call per query, which is worth the quality gain.

### Why confidence scoring?
Each entity gets a `confidence` score (0.0–1.0) from the reflection pass, based on how well the evidence supports it. Results are sorted by confidence descending so the most reliable entities appear first. This makes the system interpretable and research-grade.

### Why merge reason tracking?
When two entities are deduplicated, the system records exactly why — e.g. `"Matched on name similarity (0.91) across 2 sources"`. This makes the deduplication step transparent and auditable rather than a silent black box.

### Why Groq + Llama 3.1?
Groq is free with no credit card required, and runs Llama 3.1 at extremely high speed. For this prototype, this is the ideal balance of cost, speed, and quality. Swapping to GPT-4o or Claude is a one-line change in `config.py`.

### Why SerpAPI over Brave?
Both work. SerpAPI's free tier (100 searches/month) was sufficient for development and evaluation. Brave Search is a drop-in alternative via `SEARCH_PROVIDER=brave`.

### Why fuzzy matching over embeddings for dedup?
`rapidfuzz.token_sort_ratio` handles the vast majority of real duplicates (word-order variants, minor typos) at zero API cost and with deterministic behavior. Embedding-based dedup would be more semantically powerful but adds latency, cost, and an extra dependency. At 5–10 pages / ~50 entities per run, fuzzy matching is the right call.

### Why file-based caching?
No Redis dependency, zero setup, works offline after the first run, and easy to inspect. For a production system, Redis or a proper KV store would be preferred.

### Why async scraping but sequential LLM calls?
The bottleneck is network I/O — already handled with async aiohttp. LLM calls are fast enough sequentially for ≤10 pages. Async extraction would complicate error handling without meaningful speedup at this scale.

---

## Limitations

- **JS-rendered pages**: aiohttp + BeautifulSoup can't execute JavaScript. React SPAs return sparse content. Playwright would fix this.
- **Paywalled content**: Only preview text is accessible.
- **LLM hallucination**: The prompt instructs grounding in source text and evidence snippets provide a check, but occasional fabrication is possible.
- **Rate limits**: Groq's free tier throttles at ~30 req/min. The retry logic handles this automatically but adds latency on large queries.
- **Dedup precision**: Fuzzy string matching may over-merge similarly named but distinct entities.
```