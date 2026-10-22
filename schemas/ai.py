"""AI schemas. The *Output models are what the model must return (strict JSON schema); the others are the API answers.

The output models have no length limits on purpose: strict structured outputs accept a small subset of JSON
schema, so the lists are trimmed in services/ai.py instead.
"""
from typing import Literal

from pydantic import BaseModel

from services.catalog import MODULES

ModuleKey = Literal[tuple(MODULES)]  # the model can only suggest modules of the catalog


class AIStatus(BaseModel):
    configured: bool
    provider: str
    model: str


# ---------- 1. Second opinion on the scope ----------

class _Suggestion(BaseModel):
    key: ModuleKey
    reason: str


class ScopeReviewOutput(BaseModel):
    suggestions: list[_Suggestion]
    missing_details: list[str]


class ModuleSuggestion(BaseModel):
    """Ready to send to POST /quotes/{id}/items with the "Agregar" button."""
    key: str
    name: str
    category: str
    hours_likely: float
    split: dict[str, float]
    reason: str


class ScopeReview(BaseModel):
    quote_id: int
    suggestions: list[ModuleSuggestion]
    missing_details: list[str]


# ---------- 2. Price explanation ----------

class PriceExplanationOutput(BaseModel):
    summary: str
    drivers: list[str]
    ways_to_lower: list[str]


class PriceExplanation(PriceExplanationOutput):
    quote_id: int


# ---------- 3. Questions and risks for the client ----------

class _Risk(BaseModel):
    risk: str
    mitigation: str


class ClientQuestionsOutput(BaseModel):
    questions: list[str]
    risks: list[_Risk]


class Risk(_Risk):
    pass


class ClientQuestions(BaseModel):
    quote_id: int
    questions: list[str]
    risks: list[Risk]


# ---------- 4. Proposal wording ----------

class _Section(BaseModel):
    index: int
    text: str


class ProposalWordingOutput(BaseModel):
    sections: list[_Section]


class SectionChange(BaseModel):
    heading: str
    original: str
    improved: str


class ProposalWording(BaseModel):
    quote_id: int
    sections: list[SectionChange]
    # Sections whose new text changed a number: they are left out, the user never sees them
    discarded: list[str]
