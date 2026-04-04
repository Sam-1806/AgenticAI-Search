"""
api.py — FastAPI backend + beautiful single-page frontend.
"""

from __future__ import annotations
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import config
from main import run_pipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="Agentic Search API", version="1.0.0")


class SearchRequest(BaseModel):
    query: str
    num_results: int | None = None


class SearchResponse(BaseModel):
    query: str
    entity_count: int
    entities: list[dict]


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/search", response_model=SearchResponse)
async def search_endpoint(req: SearchRequest) -> SearchResponse:
    logger.info("API request: query=%r", req.query)
    try:
        config.validate()
        entities = await run_pipeline(query=req.query, num_results=req.num_results)
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=f"Config error: {exc}")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Pipeline error: {exc}")

    return SearchResponse(query=req.query, entity_count=len(entities), entities=entities)


@app.get("/health")
async def health():
    return {"status": "ok"}


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agentic Search</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --accent: #7c6bff;
    --accent2: #ff6b9d;
    --accent3: #6bffd8;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --card-bg: #13131e;
  }

  html { scroll-behavior: smooth; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Animated background grid */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(124,107,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(124,107,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  /* Glowing orbs */
  body::after {
    content: '';
    position: fixed;
    top: -20%;
    left: -10%;
    width: 60%;
    height: 60%;
    background: radial-gradient(ellipse, rgba(124,107,255,0.08) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }

  .orb2 {
    position: fixed;
    bottom: -20%;
    right: -10%;
    width: 50%;
    height: 50%;
    background: radial-gradient(ellipse, rgba(255,107,157,0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }

  .wrapper {
    position: relative;
    z-index: 1;
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 24px;
  }

  /* Header */
  header {
    padding: 60px 0 40px;
    animation: fadeDown 0.8s ease both;
  }

  .header-tag {
    display: inline-block;
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent3);
    border: 1px solid rgba(107,255,216,0.3);
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 20px;
  }

  h1 {
    font-family: 'Syne', sans-serif;
    font-size: clamp(42px, 7vw, 80px);
    font-weight: 800;
    line-height: 0.95;
    letter-spacing: -0.03em;
    margin-bottom: 16px;
  }

  h1 .line1 { display: block; color: var(--text); }
  h1 .line2 {
    display: block;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .subtitle {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.6;
    max-width: 480px;
    margin-top: 12px;
  }

  /* Search section */
  .search-section {
    margin: 40px 0;
    animation: fadeUp 0.8s 0.2s ease both;
  }

  .search-box {
    display: flex;
    gap: 12px;
    align-items: stretch;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 8px;
    transition: border-color 0.3s, box-shadow 0.3s;
  }

  .search-box:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(124,107,255,0.12), 0 0 40px rgba(124,107,255,0.08);
  }

  #queryInput {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text);
    font-family: 'DM Mono', monospace;
    font-size: 14px;
    padding: 14px 16px;
    placeholder-color: var(--muted);
  }

  #queryInput::placeholder { color: var(--muted); }

  .search-btn {
    background: linear-gradient(135deg, var(--accent), #9b8aff);
    border: none;
    border-radius: 10px;
    color: white;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.05em;
    padding: 14px 28px;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
    white-space: nowrap;
  }

  .search-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(124,107,255,0.4); }
  .search-btn:active { transform: translateY(0); }
  .search-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .suggestions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 12px;
  }

  .suggestion-chip {
    font-size: 11px;
    color: var(--muted);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 4px 12px;
    cursor: pointer;
    transition: all 0.2s;
    background: transparent;
    font-family: 'DM Mono', monospace;
  }

  .suggestion-chip:hover {
    color: var(--accent);
    border-color: var(--accent);
    background: rgba(124,107,255,0.08);
  }

  /* Status bar */
  #status {
    display: none;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 24px;
    font-size: 12px;
    color: var(--muted);
    animation: fadeUp 0.3s ease both;
  }

  #status.visible { display: flex; }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }

  .status-steps {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }

  .step {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border: 1px solid var(--border);
    color: var(--muted);
    transition: all 0.3s;
  }

  .step.active {
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(124,107,255,0.1);
  }

  .step.done {
    border-color: var(--accent3);
    color: var(--accent3);
    background: rgba(107,255,216,0.08);
  }

  /* Results header */
  .results-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 20px;
    gap: 12px;
    flex-wrap: wrap;
  }

  .results-title {
    font-family: 'Syne', sans-serif;
    font-size: 20px;
    font-weight: 700;
  }

  .results-count {
    font-size: 11px;
    color: var(--muted);
    border: 1px solid var(--border);
    padding: 3px 10px;
    border-radius: 20px;
  }

  /* Entity cards grid */
  #results {
    display: none;
    animation: fadeUp 0.5s ease both;
  }

  #results.visible { display: block; }

  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
    margin-bottom: 40px;
  }

  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    transition: border-color 0.25s, transform 0.25s, box-shadow 0.25s;
    animation: fadeUp 0.5s ease both;
    position: relative;
    overflow: hidden;
  }

  .card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    opacity: 0;
    transition: opacity 0.3s;
  }

  .card:hover {
    border-color: rgba(124,107,255,0.4);
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(124,107,255,0.1);
  }

  .card:hover::before { opacity: 1; }

  .card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .card-name {
    font-family: 'Syne', sans-serif;
    font-size: 17px;
    font-weight: 700;
    color: var(--text);
    line-height: 1.2;
  }

  .card-name a {
    color: inherit;
    text-decoration: none;
    transition: color 0.2s;
  }

  .card-name a:hover { color: var(--accent); }

  .category-badge {
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 3px 9px;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
    font-weight: 500;
  }

  .cat-startup { background: rgba(124,107,255,0.15); color: #9b8aff; border: 1px solid rgba(124,107,255,0.3); }
  .cat-organization { background: rgba(107,255,216,0.1); color: var(--accent3); border: 1px solid rgba(107,255,216,0.25); }
  .cat-product { background: rgba(255,107,157,0.1); color: #ff8ab5; border: 1px solid rgba(255,107,157,0.25); }
  .cat-person { background: rgba(255,200,100,0.1); color: #ffc864; border: 1px solid rgba(255,200,100,0.25); }
  .cat-concept { background: rgba(150,150,180,0.1); color: #a0a0c0; border: 1px solid rgba(150,150,180,0.2); }
  .cat-default { background: rgba(100,100,120,0.1); color: var(--muted); border: 1px solid var(--border); }

  .card-description {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.65;
    margin-bottom: 16px;
  }

  .attributes {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;
  }

  .attr-pill {
    font-size: 10px;
    color: var(--text);
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 3px 8px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .attr-key { color: var(--muted); margin-right: 4px; }

  .sources-section {
    border-top: 1px solid var(--border);
    padding-top: 14px;
    margin-top: auto;
  }

  .sources-label {
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .source-item {
    font-size: 11px;
    margin-bottom: 6px;
  }

  .source-url {
    color: var(--accent);
    text-decoration: none;
    font-size: 10px;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    opacity: 0.8;
    transition: opacity 0.2s;
  }

  .source-url:hover { opacity: 1; }

  .evidence {
    font-size: 10px;
    color: var(--muted);
    font-style: italic;
    line-height: 1.5;
    margin-top: 3px;
    border-left: 2px solid var(--border);
    padding-left: 8px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* JSON view */
  .view-toggle {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .toggle-btn {
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 4px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .toggle-btn.active {
    background: var(--surface2);
    border-color: var(--accent);
    color: var(--accent);
  }

  #jsonView {
    display: none;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    overflow-x: auto;
    margin-bottom: 40px;
  }

  #jsonView.visible { display: block; }

  #jsonView pre {
    font-size: 11px;
    line-height: 1.7;
    color: var(--text);
    white-space: pre-wrap;
    word-break: break-word;
  }

  /* Error */
  .error-box {
    background: rgba(255,80,80,0.08);
    border: 1px solid rgba(255,80,80,0.25);
    border-radius: 12px;
    padding: 20px;
    color: #ff8080;
    font-size: 13px;
    margin-bottom: 24px;
  }

  /* Footer */
  footer {
    border-top: 1px solid var(--border);
    padding: 24px 0;
    text-align: center;
    font-size: 11px;
    color: var(--muted);
    margin-top: 40px;
  }

  /* Animations */
  @keyframes fadeDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Staggered card animation */
  .card:nth-child(1) { animation-delay: 0.05s; }
  .card:nth-child(2) { animation-delay: 0.10s; }
  .card:nth-child(3) { animation-delay: 0.15s; }
  .card:nth-child(4) { animation-delay: 0.20s; }
  .card:nth-child(5) { animation-delay: 0.25s; }
  .card:nth-child(6) { animation-delay: 0.30s; }
  .card:nth-child(7) { animation-delay: 0.35s; }
  .card:nth-child(8) { animation-delay: 0.40s; }
  .card:nth-child(n+9) { animation-delay: 0.45s; }
</style>
</head>
<body>
<div class="orb2"></div>
<div class="wrapper">
  <header>
    <div class="header-tag">⬡ Agentic Search Engine</div>
    <h1>
      <span class="line1">Discover.</span>
      <span class="line2">Extract. Know.</span>
    </h1>
    <p class="subtitle">Enter any topic and watch the pipeline search the web, scrape sources, and extract structured intelligence — all traced back to evidence.</p>
  </header>

  <section class="search-section">
    <div class="search-box">
      <input
        id="queryInput"
        type="text"
        placeholder="e.g. AI startups in healthcare, open source databases..."
        autocomplete="off"
      />
      <button class="search-btn" id="searchBtn" onclick="runSearch()">
        Search →
      </button>
    </div>
    <div class="suggestions">
      <span style="font-size:11px;color:var(--muted);margin-right:4px;">Try:</span>
      <button class="suggestion-chip" onclick="fillQuery('AI startups in healthcare')">AI startups in healthcare</button>
      <button class="suggestion-chip" onclick="fillQuery('open source database tools')">open source databases</button>
      <button class="suggestion-chip" onclick="fillQuery('climate tech companies 2024')">climate tech companies</button>
      <button class="suggestion-chip" onclick="fillQuery('top VC firms in Europe')">top VC firms in Europe</button>
    </div>
  </section>

  <div id="status">
    <div class="spinner"></div>
    <div>
      <div class="status-steps">
        <span class="step" id="step-search">Search</span>
        <span style="color:var(--border)">→</span>
        <span class="step" id="step-scrape">Scrape</span>
        <span style="color:var(--border)">→</span>
        <span class="step" id="step-extract">Extract</span>
        <span style="color:var(--border)">→</span>
        <span class="step" id="step-aggregate">Aggregate</span>
      </div>
      <div id="statusText" style="margin-top:6px;font-size:11px;">Initializing pipeline...</div>
    </div>
  </div>

  <div id="errorBox" style="display:none"></div>

  <div id="results">
    <div class="results-header">
      <div>
        <div class="results-title" id="resultsTitle"></div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="results-count" id="resultsCount"></span>
        <div style="display:flex;gap:8px;align-items:center;">
  <div class="view-toggle">
    <button class="toggle-btn active" id="btnCards" onclick="switchView('cards')">Cards</button>
    <button class="toggle-btn" id="btnJson" onclick="switchView('json')">JSON</button>
  </div>
  <button class="toggle-btn" id="btnDownload" onclick="downloadJson()" style="border-color:var(--accent3);color:var(--accent3);">↓ Download</button>
</div>
      </div>
    </div>
    <div class="cards-grid" id="cardsGrid"></div>
    <div id="jsonView"><pre id="jsonContent"></pre></div>
  </div>

  <footer>Built with FastAPI · Groq · SerpAPI · BeautifulSoup · aiohttp</footer>
</div>

<script>
  let currentData = [];

  function fillQuery(q) {
    document.getElementById('queryInput').value = q;
    document.getElementById('queryInput').focus();
  }

  document.getElementById('queryInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') runSearch();
  });

  function setStep(step) {
    const steps = ['search', 'scrape', 'extract', 'aggregate'];
    const idx = steps.indexOf(step);
    steps.forEach((s, i) => {
      const el = document.getElementById('step-' + s);
      if (i < idx) { el.className = 'step done'; }
      else if (i === idx) { el.className = 'step active'; }
      else { el.className = 'step'; }
    });
  }

  function animateSteps() {
    const steps = ['search', 'scrape', 'extract', 'aggregate'];
    const messages = [
      'Searching the web for relevant results...',
      'Scraping and cleaning page content...',
      'Extracting structured entities with LLM...',
      'Deduplicating and merging results...'
    ];
    let i = 0;
    setStep(steps[0]);
    document.getElementById('statusText').textContent = messages[0];
    const interval = setInterval(() => {
      i++;
      if (i < steps.length) {
        setStep(steps[i]);
        document.getElementById('statusText').textContent = messages[i];
      } else {
        clearInterval(interval);
      }
    }, 4000);
    return interval;
  }

  async function runSearch() {
    const query = document.getElementById('queryInput').value.trim();
    if (!query) return;

    const btn = document.getElementById('searchBtn');
    const status = document.getElementById('status');
    const results = document.getElementById('results');
    const errorBox = document.getElementById('errorBox');

    btn.disabled = true;
    btn.textContent = 'Searching...';
    status.className = 'visible';
    results.className = '';
    errorBox.style.display = 'none';
    document.getElementById('cardsGrid').innerHTML = '';

    const interval = animateSteps();

    try {
      const resp = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      clearInterval(interval);

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Search failed');
      }

      const data = await resp.json();
      currentData = data.entities;

      status.className = '';
      renderResults(query, data);

    } catch (err) {
      clearInterval(interval);
      status.className = '';
      errorBox.style.display = 'block';
      errorBox.className = 'error-box';
      errorBox.textContent = '⚠ ' + err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Search →';
    }
  }

  function getCategoryClass(cat) {
    const map = { startup: 'cat-startup', organization: 'cat-organization', product: 'cat-product', person: 'cat-person', concept: 'cat-concept' };
    return map[cat?.toLowerCase()] || 'cat-default';
  }

  function renderResults(query, data) {
    document.getElementById('resultsTitle').textContent = '"' + query + '"';
    document.getElementById('resultsCount').textContent = data.entity_count + ' entities';
    document.getElementById('jsonContent').textContent = JSON.stringify(data.entities, null, 2);

    const grid = document.getElementById('cardsGrid');
    grid.innerHTML = '';

    data.entities.forEach((e, idx) => {
      const attrs = Object.entries(e.attributes || {}).slice(0, 4);
      const sources = e.sources || [];

      const attrsHtml = attrs.map(([k, v]) => {
        const val = Array.isArray(v) ? v.join(', ') : String(v);
        return `<span class="attr-pill"><span class="attr-key">${k}:</span>${val.slice(0, 30)}${val.length > 30 ? '…' : ''}</span>`;
      }).join('');

      const sourcesHtml = sources.slice(0, 2).map(s => `
        <div class="source-item">
          <a class="source-url" href="${s.url}" target="_blank" title="${s.url}">${s.url.replace(/^https?:\/\//, '').slice(0, 50)}${s.url.length > 50 ? '…' : ''}</a>
          ${s.evidence ? `<div class="evidence">"${s.evidence}"</div>` : ''}
        </div>
      `).join('');

      const nameHtml = e.website
        ? `<a href="${e.website}" target="_blank">${e.name}</a>`
        : e.name;

      grid.innerHTML += `
        <div class="card">
          <div class="card-header">
            <div class="card-name">${nameHtml}</div>
            <span class="category-badge ${getCategoryClass(e.category)}">${e.category}</span>
          </div>
          <p class="card-description">${e.description || '—'}</p>
          ${attrsHtml ? `<div class="attributes">${attrsHtml}</div>` : ''}
          <div class="sources-section">
            <div class="sources-label">Sources</div>
            ${sourcesHtml || '<span style="font-size:11px;color:var(--muted)">No sources</span>'}
          </div>
        </div>
      `;
    });

    document.getElementById('results').className = 'visible';
    document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function switchView(view) {
    const cards = document.getElementById('cardsGrid');
    const json = document.getElementById('jsonView');
    const btnCards = document.getElementById('btnCards');
    const btnJson = document.getElementById('btnJson');

    if (view === 'cards') {
      cards.style.display = 'grid';
      json.className = '';
      btnCards.className = 'toggle-btn active';
      btnJson.className = 'toggle-btn';
    } else {
      cards.style.display = 'none';
      json.className = 'visible';
      btnCards.className = 'toggle-btn';
      btnJson.className = 'toggle-btn active';
    }
  }
  function downloadJson() {
  const blob = new Blob([JSON.stringify(currentData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'agentic_search_results.json';
  a.click();
  URL.revokeObjectURL(url);
}
</script>
</body>
</html>
"""