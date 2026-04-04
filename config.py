"""
config.py — Central configuration and API key management.

Loads settings from environment variables with sensible defaults.
All tuneable parameters live here so nothing is hardcoded downstream.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
load_dotenv()


@dataclass
class Config:
    # --- API Keys ---
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    serpapi_key: str = field(default_factory=lambda: os.environ.get("SERPAPI_KEY", ""))
    brave_api_key: str = field(default_factory=lambda: os.environ.get("BRAVE_API_KEY", ""))
    # --- Gemini settings ---
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    gemini_model: str = "gemini-2.0-flash-lite"

    # --- Groq settings ---
    groq_api_key: str = field(default_factory=lambda: os.environ.get("GROQ_API_KEY", ""))
    groq_model: str = "llama-3.1-8b-instant"

    # --- Search settings ---
    search_provider: str = field(default_factory=lambda: os.environ.get("SEARCH_PROVIDER", "brave"))  # "brave" | "serpapi"
    max_results: int = 8          # How many search results to process
    search_timeout: int = 10      # seconds

    # --- Scraper settings ---
    scrape_timeout: int = 12      # seconds per page
    max_content_chars: int = 6000 # clip page text to keep LLM costs low
    max_concurrent_scrapes: int = 5

    # --- LLM settings ---
    openai_model: str = "gpt-4o-mini"   # cheap + fast; swap to gpt-4o for higher quality
    llm_temperature: float = 0.0        # deterministic extraction
    llm_max_tokens: int = 2048
    max_entities_per_page: int = 5      # guard against hallucination sprawl
    llm_call_delay: float = 4.0  # seconds between LLM calls


    # --- Aggregation ---
    dedup_threshold: float = 0.82       # fuzzy-match similarity cutoff (0–1)

    # --- Caching ---
    cache_dir: str = ".cache"
    use_cache: bool = True

    # --- FastAPI ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    def validate(self) -> None:
        if not self.groq_api_key:
            raise EnvironmentError("GROQ_API_KEY is not set.")
        if self.search_provider == "brave" and not self.brave_api_key:
            raise EnvironmentError("BRAVE_API_KEY is not set (required when SEARCH_PROVIDER=brave).")
        if self.search_provider == "serpapi" and not self.serpapi_key:
            raise EnvironmentError("SERPAPI_KEY is not set (required when SEARCH_PROVIDER=serpapi).")

# Module-level singleton — import this everywhere.
config = Config()
