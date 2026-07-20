"""
Abstract structural metadata schemas for graduate application essays.

DESIGN RULE: These models intentionally contain NO fields for:
  - Source sentences, phrases, or verbatim excerpts
  - Personal stories, identity details, or biographical facts
  - Research project names, lab names, or advisor names
  - Any content that could re-identify the original author

All models use extra="forbid" to prevent accidental field additions.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProgramType(str, Enum):
    PHD = "phd"
    MASTERS = "masters"
    PROFESSIONAL = "professional"
    UNKNOWN = "unknown"


class NarrativeArc(str, Enum):
    PROBLEM_SOLUTION = "problem_solution"
    CHRONOLOGICAL_JOURNEY = "chronological_journey"
    EXPERTISE_DEMONSTRATION = "expertise_demonstration"
    FUTURE_VISION = "future_vision"
    THEMATIC = "thematic"
    UNKNOWN = "unknown"


class MotivationPlacement(str, Enum):
    OPENING = "opening"
    MIDDLE = "middle"
    CLOSING = "closing"
    DISTRIBUTED = "distributed"


class EssayStructurePattern(BaseModel):
    """Abstract description of essay structure — no verbatim content."""

    model_config = ConfigDict(extra="forbid")

    section_order: list[str] = Field(
        description=(
            "Ordered abstract section labels, e.g. "
            "['motivation', 'background', 'research', 'goals']. "
            "Labels only — no copied text."
        )
    )
    opening_move: str = Field(
        description=(
            "Abstract rhetorical label for the opening strategy, "
            "e.g. 'hook_question' or 'hook_observation'. Not the actual text."
        )
    )
    closing_move: str = Field(
        description=(
            "Abstract rhetorical label for the closing strategy, "
            "e.g. 'closing_vision' or 'contribution_statement'. Not the actual text."
        )
    )
    paragraph_count: int = Field(ge=1, description="Total paragraph count")


class AbstractWritingPattern(BaseModel):
    """Abstract writing-style metadata — no verbatim content."""

    model_config = ConfigDict(extra="forbid")

    narrative_arc: NarrativeArc
    motivation_placement: MotivationPlacement
    research_emphasis_level: str = Field(
        description="Abstract level: 'low' | 'medium' | 'high'"
    )
    future_goals_explicit: bool = Field(
        description="Whether the essay explicitly states post-degree goals"
    )
    interdisciplinary: bool = Field(
        description="Whether the essay spans multiple academic disciplines"
    )


class DocumentAbstraction(BaseModel):
    """
    Complete abstract metadata record for one graduate application essay.

    This model MUST NOT contain any of the following:
      - Verbatim sentences or phrases from the source document
      - Quoted passages or paraphrased excerpts
      - Personal stories, experiences, or biographical details
      - Names of people, institutions, projects, or advisors
      - Any information that could identify the essay's author
    """

    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(description="Derived from filename — no PII")
    program_type: ProgramType
    field_of_study: str = Field(
        description=(
            "General academic field label, e.g. 'computer_science', "
            "'biology', 'economics'. No institution names."
        )
    )
    word_count: int = Field(ge=0, description="Approximate word count of the essay")
    structure: EssayStructurePattern
    writing_patterns: AbstractWritingPattern
    rhetorical_moves: list[str] = Field(
        description=(
            "Ordered list of abstract rhetorical move labels from the taxonomy. "
            "Labels only — no copied text."
        )
    )
    theme_keywords: list[str] = Field(
        description=(
            "Generic topical keywords (common nouns, field terms). "
            "No proper nouns, no names, no identifying terms."
        )
    )
