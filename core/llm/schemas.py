"""
Pydantic schemas for LLM-structured I/O.

Kept separate from core/models.py (dataclasses) to avoid mixing
validation styles. These are LLM boundary types only; downstream
code converts them into domain models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class MessageExtraction(BaseModel):
    """Structured data extracted from a customer message by the LLM."""

    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    locations: List[str] = Field(default_factory=list)
    interest_level: str = "cold"   # "hot" | "warm" | "cold"
    intent: str = "browse"         # "buy" | "invest" | "rent" | "browse"
    property_types: List[str] = Field(default_factory=list)
    bedroom_count: Optional[int] = None
    key_phrases: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


class SuggestionOutput(BaseModel):
    """A single reply suggestion returned by the LLM."""

    message: str
    tactics: List[str]
    reasoning: str
