"""
aggregator.py — Entity deduplication and merging.

The core challenge: the same real-world entity (e.g. "Google DeepMind")
might appear as "DeepMind", "Google DeepMind", or "Deepmind AI" across
different pages. We want one canonical entry with multiple sources.

Approach:
1. Normalise names (lowercase, strip punctuation).
2. Build a similarity matrix using rapidfuzz token_sort_ratio.
   token_sort_ratio handles word-order differences well (e.g. "DeepMind Google"
   vs "Google DeepMind"), which simple string distance misses.
3. Greedily merge entity pairs that exceed the dedup_threshold.

Trade-off: O(n²) similarity — fine for n ≤ ~50 entities per run.
For larger pipelines, approximate nearest-neighbour (e.g. via embeddings)
would be more scalable, but adds significant complexity.
"""

from __future__ import annotations
import logging
import re

from rapidfuzz import fuzz

from config import config
from schema import Entity


logger = logging.getLogger(__name__)


def _normalise(name: str) -> str:
    """Lowercase and strip punctuation for stable comparison."""
    return re.sub(r"[^\w\s]", "", name.lower()).strip()



def _similarity(a: str, b: str) -> float:
    """
    Return a 0–1 similarity score between two entity names.

    token_sort_ratio sorts tokens alphabetically before comparing,
    making it robust to word-order variants.
    """
    return fuzz.token_sort_ratio(_normalise(a), _normalise(b)) / 100.0


def deduplicate(entities: list[Entity]) -> list[Entity]:
    """
    Merge entities whose names are sufficiently similar.

    Algorithm:
    - Maintain a list of "canonical" entities (the merged results).
    - For each incoming entity, check against all existing canonicals.
    - If a match is found above threshold, merge; otherwise add as new.

    This is a single-pass greedy approach — not optimal but deterministic
    and easy to reason about.
    """
    if not entities:
        return []

    canonical: list[Entity] = []

    for entity in entities:
        merged = False
        for i, canon in enumerate(canonical):
            sim = _similarity(entity.name, canon.name)
            if sim >= config.dedup_threshold:
                merge_reason = (
                    f"Matched on name similarity ({sim:.2f}) "
                    f"across {len(canon.sources) + len(entity.sources)} sources"
                )
                merged_entity = canon.merge(entity)
                merged_entity.merge_reason = merge_reason
                canonical[i] = merged_entity
                logger.debug(
                    "Merged %r into %r — %s",
                    entity.name, canon.name, merge_reason,
                )
                merged = True
                break
        if not merged:
            canonical.append(entity)

    logger.info(
        "Deduplication: %d → %d entities (threshold=%.2f)",
        len(entities), len(canonical), config.dedup_threshold,
    )
    return canonical