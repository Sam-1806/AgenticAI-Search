"""
extractor.py — LLM-based structured entity extraction using Groq.
"""

from __future__ import annotations
import json
import logging
import time
from typing import Any

from groq import Groq, APIError, RateLimitError

from config import config
from schema import Entity, Source

logger = logging.getLogger(__name__)


def _call_groq_with_retry(prompt: str, retries: int = 3, backoff: float = 2.0) -> str:
    client = Groq(api_key=config.groq_api_key)
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model=config.groq_model,
                messages=[
                    {"role": "system", "content": "You are a precise information-extraction engine. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"
        except RateLimitError:
            wait = backoff ** attempt
            logger.warning("Rate limited. Retrying in %.1fs (attempt %d/%d)...", wait, attempt, retries)
            time.sleep(wait)
        except APIError as exc:
            if attempt == retries:
                raise
            wait = backoff ** attempt
            logger.warning("Groq API error: %s. Retrying in %.1fs...", exc, wait)
            time.sleep(wait)
    return "{}"


_EXTRACTION_PROMPT = """\
Given a topic query and a webpage's text content, extract up to {max_entities} \
distinct entities that are directly relevant to the query.

Return ONLY a JSON object with the key "entities" — an array of objects.
Each object must have:
  name        (string)  — canonical entity name
  category    (string)  — e.g. "startup", "product", "person", "organization"
  description (string)  — 1-3 sentence summary grounded in the source text
  website     (string|null) — official URL if mentioned, else null
  attributes  (object)  — domain-relevant key-value pairs found in the text
  source_url  (string)  — the URL you are extracting from
  evidence_text (string) — a verbatim snippet (<=200 chars) from the page

Rules:
- Only include entities explicitly mentioned in the provided text.
- Do not invent attributes or evidence.
- If a field is unknown, omit it or use null.
- evidence_text must be a direct quote from the content.

Query: {query}

Source URL: {url}

Page content:
{text}
"""


def _parse_entities(raw_json: str, source_url: str) -> list[Entity]:
    try:
        data: dict[str, Any] = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM JSON: %s", exc)
        return []

    entities: list[Entity] = []
    for raw in data.get("entities", []):
        try:
            entity = Entity(
                name=raw["name"],
                category=raw.get("category", "unknown"),
                description=raw.get("description", ""),
                website=raw.get("website"),
                attributes=raw.get("attributes", {}),
                sources=[Source(url=source_url, evidence=raw.get("evidence_text", ""))],
            )
            entities.append(entity)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed entity %r: %s", raw.get("name"), exc)

    return entities


def extract_entities(query: str, url: str, text: str) -> list[Entity]:
    if not text.strip():
        return []

    prompt = _EXTRACTION_PROMPT.format(
        max_entities=config.max_entities_per_page,
        query=query,
        url=url,
        text=text,
    )

    logger.info("Extracting entities from %s", url)
    try:
        raw = _call_groq_with_retry(prompt)
    except Exception as exc:
        logger.error("Groq extraction failed for %s: %s", url, exc)
        return []

    entities = _parse_entities(raw, source_url=url)
    logger.info("Extracted %d entities from %s", len(entities), url)
    return entities