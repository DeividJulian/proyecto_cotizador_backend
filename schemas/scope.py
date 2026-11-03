from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

Level = Literal["low", "medium", "high"]  # complexity and confidence
Source = Literal["ai", "manual"]  # ai: detected by the analysis

ScopeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=20000)]


class ScopeInput(BaseModel):
    scope_description: ScopeText


class ScopeModule(BaseModel):
    key: str
    name: str
    category: str
    complexity: Level
    matched_keywords: list[str]
    reasons: str


class Analysis(BaseModel):
    """Result of the scope analysis. A quote that was never analyzed has the empty lists and no confidence."""
    # The API always sends every key (null when empty): the published output schema marks them as required
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    modules: list[ScopeModule] = []
    high_complexity_signals: list[str] = []
    low_complexity_signals: list[str] = []
    confidence: Level | None = None
    warnings: list[str] = []


class RoleHours(BaseModel):
    optimistic: float
    likely: float
    pessimistic: float
    expected: float


class Estimate(BaseModel):
    """PERT hours by role and in total. Empty (all null) while the quote has no modules."""
    # The API always sends every key (null when empty): the published output schema marks them as required
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    by_role: dict[str, RoleHours] | None = None
    hours_optimistic: float | None = None
    hours_likely: float | None = None
    hours_pessimistic: float | None = None
    hours_expected: float | None = None
    confidence: Level | None = None


class EstimatedItem(BaseModel):
    name: str
    category: str
    complexity: Level
    source: Source
    split: dict[str, float]
    reasons: str
    hours_optimistic: float
    hours_likely: float
    hours_pessimistic: float
    hours_expected: float


class ScopeEstimate(BaseModel):
    analysis: Analysis
    items: list[EstimatedItem]
    estimate: Estimate
