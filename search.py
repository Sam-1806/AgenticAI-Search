"""
search.py — Web search API abstraction.

Supports Brave Search and SerpAPI. The active provider is selected via
config.search_provider. Adding a new provider means implementing one
function and registering it in `run_search`.

Trade-off: we use synchronous requests here because search is a single
sequential call at the start of the pipeline — no benefit to async.
"""

from __future__ import annotations
import logging
import requests
from typing import TypedDict

from config import config

logger = logging.getLogger(__name__)


class SearchResult(TypedDict):
    title: str
    url: str
    snippet: str


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _search_brave(query: str, num_results: int) -> list[SearchResult]:
    """Call the Brave Search Web Search API."""
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": config.brave_api_key,
    }
    params = {"q": query, "count": num_results, "text_decorations": False}

    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers=headers,
        params=params,
        timeout=config.search_timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    results: list[SearchResult] = []
    for item in data.get("web", {}).get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
            )
        )
    return results


def _search_serpapi(query: str, num_results: int) -> list[SearchResult]:
    """Call the SerpAPI Google Search endpoint."""
    params = {
        "q": query,
        "num": num_results,
        "api_key": config.serpapi_key,
        "engine": "google",
    }
    resp = requests.get(
        "https://serpapi.com/search",
        params=params,
        timeout=config.search_timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    results: list[SearchResult] = []
    for item in data.get("organic_results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
            )
        )
    return results


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_search(query: str, num_results: int | None = None) -> list[SearchResult]:
    """
    Execute a web search and return a normalised list of results.

    Raises RuntimeError on API failure so the caller can decide whether
    to abort or continue with partial data.
    """
    n = num_results or config.max_results
    provider = config.search_provider.lower()

    logger.info("Searching [provider=%s] query=%r n=%d", provider, query, n)

    try:
        if provider == "brave":
            results = _search_brave(query, n)
        elif provider == "serpapi":
            results = _search_serpapi(query, n)
        else:
            raise ValueError(f"Unknown search provider: {provider!r}")
    except requests.RequestException as exc:
        raise RuntimeError(f"Search API request failed: {exc}") from exc

    logger.info("Search returned %d results", len(results))
    return results
