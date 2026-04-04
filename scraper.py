"""
scraper.py — Async webpage fetcher and content cleaner.

Design decisions:
- aiohttp for concurrent fetching (big speedup vs sequential requests).
- BeautifulSoup for robust HTML parsing and noise removal.
- We strip scripts, styles, nav, footer, aside — these add tokens without
  adding factual content.
- Content is capped at config.max_content_chars to control LLM costs.
- A simple file-based cache avoids re-fetching on repeated runs.
"""

from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import os
import re
from typing import NamedTuple

import aiohttp
from bs4 import BeautifulSoup

from config import config

logger = logging.getLogger(__name__)

# Tags that rarely contain useful article content
_NOISE_TAGS = [
    "script", "style", "noscript", "nav", "footer", "header",
    "aside", "form", "button", "svg", "img",
]

# User-agent that most sites accept
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AgenticSearchBot/1.0; "
        "+https://github.com/example/agentic-search)"
    )
}


class ScrapedPage(NamedTuple):
    url: str
    text: str          # cleaned, truncated body text
    success: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(url: str) -> str:
    key = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(config.cache_dir, f"{key}.json")


def _load_cache(url: str) -> str | None:
    if not config.use_cache:
        return None
    path = _cache_path(url)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("text")
    return None


def _save_cache(url: str, text: str) -> None:
    if not config.use_cache:
        return
    os.makedirs(config.cache_dir, exist_ok=True)
    with open(_cache_path(url), "w") as f:
        json.dump({"url": url, "text": text}, f)


# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------

def _clean_html(html: str) -> str:
    """Extract main text from HTML, removing boilerplate."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noisy tags in-place
    for tag in soup(  # type: ignore[call-overload]
        _NOISE_TAGS
    ):
        tag.decompose()

    # Prefer <main> or <article> if present — higher signal density
    main = soup.find("main") or soup.find("article")
    root = main if main else soup.body or soup

    # Collapse whitespace
    text = root.get_text(separator=" ", strip=True)  # type: ignore[union-attr]
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate to keep LLM context manageable
    return text[: config.max_content_chars]


# ---------------------------------------------------------------------------
# Async fetching
# ---------------------------------------------------------------------------

async def _fetch_one(
    session: aiohttp.ClientSession, url: str
) -> ScrapedPage:
    """Fetch and clean a single URL. Returns a failed ScrapedPage on error."""
    cached = _load_cache(url)
    if cached is not None:
        logger.debug("Cache hit: %s", url)
        return ScrapedPage(url=url, text=cached, success=True)

    try:
        async with session.get(
            url,
            headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=config.scrape_timeout),
            allow_redirects=True,
            ssl=False,  # some sites have cert issues; content is still readable
        ) as resp:
            if resp.status >= 400:
                return ScrapedPage(
                    url=url, text="", success=False,
                    error=f"HTTP {resp.status}"
                )
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return ScrapedPage(
                    url=url, text="", success=False,
                    error=f"Non-HTML content-type: {content_type}"
                )
            html = await resp.text(errors="replace")
    except aiohttp.ClientError as exc:
        return ScrapedPage(url=url, text="", success=False, error=str(exc))
    except asyncio.TimeoutError:
        return ScrapedPage(url=url, text="", success=False, error="Timeout")

    text = _clean_html(html)
    if text:
        _save_cache(url, text)

    logger.debug("Scraped %s → %d chars", url, len(text))
    return ScrapedPage(url=url, text=text, success=True)


async def scrape_urls(urls: list[str]) -> list[ScrapedPage]:
    """
    Fetch all URLs concurrently, capped at max_concurrent_scrapes.

    Returns one ScrapedPage per URL (success or failure).
    """
    sem = asyncio.Semaphore(config.max_concurrent_scrapes)

    async def bounded_fetch(session: aiohttp.ClientSession, url: str) -> ScrapedPage:
        async with sem:
            return await _fetch_one(session, url)

    connector = aiohttp.TCPConnector(limit=config.max_concurrent_scrapes)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [bounded_fetch(session, url) for url in urls]
        pages = await asyncio.gather(*tasks)

    successes = sum(1 for p in pages if p.success)
    logger.info("Scraped %d/%d URLs successfully", successes, len(urls))
    return list(pages)


def scrape_urls_sync(urls: list[str]) -> list[ScrapedPage]:
    """Synchronous entry point — runs the async loop internally."""
    return asyncio.run(scrape_urls(urls))
