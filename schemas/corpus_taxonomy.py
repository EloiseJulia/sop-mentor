"""
Corpus-level taxonomy schema — aggregated from data/abstract/*.json only.

Contains no raw text, excerpts, or identifying information.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ArcFrequency(BaseModel):
    """Frequency record for one narrative arc in the corpus."""

    model_config = ConfigDict(extra="forbid")

    arc: str
    count: int = Field(ge=0)
    frequency: float = Field(ge=0.0, le=1.0, description="Fraction of corpus documents")


class CorpusTaxonomy(BaseModel):
    """
    Aggregated abstract taxonomy of the essay corpus.

    Derived exclusively from data/abstract/*.json — never from raw or
    parsed documents. Contains no essay text or identifying information.
    """

    model_config = ConfigDict(extra="forbid")

    total_documents: int = Field(ge=0)
    program_type_counts: dict[str, int] = Field(
        description="Counts keyed by ProgramType value"
    )
    field_counts: dict[str, int] = Field(
        description="Counts keyed by field_of_study label"
    )
    narrative_arc_distribution: list[ArcFrequency] = Field(
        description="Sorted most-common first"
    )
    top_rhetorical_moves: list[str] = Field(
        description="Most frequent abstract rhetorical move labels across the corpus"
    )
    top_theme_keywords: list[str] = Field(
        description="Most frequent generic theme keywords across the corpus"
    )
    avg_word_count: float = Field(ge=0.0)
    avg_paragraph_count: float = Field(ge=0.0)
    pct_future_goals_explicit: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of documents with explicit future goals"
    )
    pct_interdisciplinary: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of documents flagged as interdisciplinary"
    )
