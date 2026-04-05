"""
main.py — Pipeline orchestrator and CLI entry point.

Run:
    python main.py "AI startups in healthcare"
    python main.py "AI startups in healthcare" --num-results 10 --output results.json

The pipeline is intentionally linear and easy to follow:
    search → scrape → extract → aggregate → output
"""

from __future__ import annotations
import argparse
import json
import logging
import sys
import asyncio

from config import config
from search import run_search
from scraper import scrape_urls, scrape_urls_sync
from extractor import extract_entities
from aggregator import deduplicate
from schema import Entity
from extractor import extract_entities, reflect_entities

# ---------------------------------------------------------------------------
# Logging — structured single-line format; easy to grep in CI / log aggregators
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(query: str, num_results: int | None = None) -> list[dict]:
    """
    Full end-to-end pipeline.

    Returns a list of plain dicts (JSON-serialisable) ready for output.
    """
    config.validate()

    # 1. Search
    logger.info("=== STEP 1: Search ===")
    search_results = run_search(query, num_results=num_results)
    if not search_results:
        logger.warning("No search results returned. Exiting.")
        return []

    urls = [r["url"] for r in search_results]
    logger.info("URLs to scrape: %s", urls)

    # 2. Scrape
    logger.info("=== STEP 2: Scrape ===")
    pages = await scrape_urls(urls)
    usable_pages = [p for p in pages if p.success and p.text.strip()]
    logger.info("%d/%d pages usable after scraping", len(usable_pages), len(pages))

    if not usable_pages:
        logger.warning("No usable page content. Exiting.")
        return []

    # 3. Extract
    logger.info("=== STEP 3: Extract ===")
    all_entities: list[Entity] = []
    for page in usable_pages:
        entities = extract_entities(query=query, url=page.url, text=page.text)
        all_entities.extend(entities)

    logger.info("Total raw entities extracted: %d", len(all_entities))

    if not all_entities:
        logger.warning("LLM returned no entities. Check your query or page content.")
        return []

    # 4. Deduplicate & aggregate
    logger.info("=== STEP 4: Aggregate ===")
    final_entities = deduplicate(all_entities)

    # 5. Reflection pass
    logger.info("=== STEP 5: Reflect ===")
    final_entities = reflect_entities(query=query, entities=final_entities)


    # 5. Serialise
    output = [e.model_dump() for e in final_entities]
    logger.info("=== DONE: %d entities returned ===", len(output))
    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agentic Search — extract structured entities from the web."
    )
    parser.add_argument("query", help='Topic to research, e.g. "AI startups in healthcare"')
    parser.add_argument(
        "--num-results", type=int, default=None,
        help=f"Number of search results to process (default: {config.max_results})",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Write JSON output to this file (default: stdout)",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable the scrape cache",
    )
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pretty-print JSON output (default: true)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.no_cache:
        config.use_cache = False

    try:
        results = asyncio.run(run_pipeline(query=args.query, num_results=args.num_results))
    except EnvironmentError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)
    except RuntimeError as exc:
        logger.error("Pipeline error: %s", exc)
        sys.exit(1)

    indent = 2 if args.pretty else None
    json_output = json.dumps(results, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        logger.info("Results written to %s", args.output)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
