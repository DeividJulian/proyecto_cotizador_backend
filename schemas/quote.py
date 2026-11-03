from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from schemas.finance import Financials
from schemas.scope import Analysis, Estimate, ScopeText
from services.catalog import CUSTOM

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Status = Literal["draft", "sent", "accepted", "rejected"]
Complexity = Literal["low", "medium", "high"]


class QuoteCreate(BaseModel):
    title: Title
    scope_description: ScopeText
    client_name: ShortText | None = None  # optional: who the project is for
    client_company: ShortText | None = None
    margin_pct: float = Field(default=30.0, ge=0, le=200)
    contingency_pct: float = Field(default=10.0, ge=0, le=100)
    discount_pct: float = Field(default=0.0, ge=0, le=50)
    vat_pct: float = Field(default=19.0, ge=0, le=30)


class QuoteUpdate(BaseModel):
    title: Title | None = None
    scope_description: ScopeText | None = None
    client_name: ShortText | None = None
    client_company: ShortText | None = None
    margin_pct: float | None = Field(default=None, ge=0, le=200)
    contingency_pct: float | None = Field(default=None, ge=0, le=100)
    discount_pct: float | None = Field(default=None, ge=0, le=50)
    vat_pct: float | None = Field(default=None, ge=0, le=30)


class StatusChange(BaseModel):
    status: Status


class ItemCreate(BaseModel):
    name: ItemName
    category: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] = CUSTOM
    complexity: Complexity = "medium"
    hours_likely: float = Field(gt=0, le=5000)
    split: dict[str, float] | None = None


class ItemUpdate(BaseModel):
    name: ItemName | None = None
    complexity: Complexity | None = None
    hours_likely: float | None = Field(default=None, gt=0, le=5000)
    split: dict[str, float] | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    complexity: str
    source: str
    hours_optimistic: float
    hours_likely: float
    hours_pessimistic: float
    hours_expected: float
    split: dict[str, float]
    reasons: str


class QuoteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    client_name: str | None
    client_company: str | None
    status: str
    total: int
    created_at: datetime
    updated_at: datetime


class QuoteOut(QuoteSummary):
    scope_description: str
    margin_pct: float
    contingency_pct: float
    discount_pct: float
    vat_pct: float
    analysis: Analysis
    estimate: Estimate
    financials: Financials
    proposal: str | None
    items: list[ItemOut]


class QuoteCard(BaseModel):
    """Compact view of a quote for cards."""
    id: int
    title: str
    client: str | None
    status: str
    modules: int
    hours_expected: float
    hours_range: list[float]
    confidence: str | None
    duration_weeks: int
    total: int
    has_proposal: bool


class SimilarQuote(BaseModel):
    id: int
    title: str
    status: str
    total: int
    similarity: float
