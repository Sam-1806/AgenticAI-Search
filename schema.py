"""
schema.py — Pydantic models for the entity pipeline.

Keeping the schema in one place makes it easy to evolve the shape of
extracted data without hunting through every file.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, HttpUrl


class Source(BaseModel):
    """A single traceable source for an entity."""
    url: str
    evidence: str = Field(
        description="Verbatim snippet from the page that grounds this entity."
    )


class Entity(BaseModel):
    """
    A structured entity extracted from web content.

    `attributes` is intentionally open-ended: the LLM populates it with
    domain-specific fields (e.g. funding, founded_year, HQ) without
    requiring schema changes per query.
    """
    name: str
    category: str
    description: str
    website: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    confidence: float = 1.0
    merge_reason: str | None = None

    def merge(self, other: "Entity") -> "Entity":
        """
        Non-destructively merge another entity into self.

        Strategy:
        - Keep the longer / more informative description.
        - Union attributes (self wins on conflicts — first source wins).
        - Append new sources without duplicating by URL.
        """
        merged_description = (
            self.description if len(self.description) >= len(other.description)
            else other.description
        )
        merged_website = self.website or other.website
        merged_attributes = {**other.attributes, **self.attributes}  # self wins

        existing_urls = {s.url for s in self.sources}
        new_sources = [s for s in other.sources if s.url not in existing_urls]

        return Entity(
            name=self.name,
            category=self.category,
            description=merged_description,
            website=merged_website,
            attributes=merged_attributes,
            sources=self.sources + new_sources,
        )


class ExtractionResult(BaseModel):
    """Wrapper around a list of entities returned by the LLM."""
    entities: list[Entity] = Field(default_factory=list)
