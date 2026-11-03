from pydantic import BaseModel, ConfigDict, Field


class SimulationInput(BaseModel):
    hours_by_role: dict[str, float] = Field(min_length=1)
    margin_pct: float = Field(default=30.0, ge=0, le=200)
    contingency_pct: float = Field(default=10.0, ge=0, le=100)
    discount_pct: float = Field(default=0.0, ge=0, le=50)
    vat_pct: float = Field(default=19.0, ge=0, le=30)


class RoleCost(BaseModel):
    role: str
    hours: float
    hourly_rate: int
    cost: int


class Milestone(BaseModel):
    name: str
    percentage: int
    week: int
    amount: int


class FinanceParams(BaseModel):
    margin_pct: float
    contingency_pct: float
    discount_pct: float
    vat_pct: float


class Financials(BaseModel):
    """Price in whole Colombian pesos. Empty (all null) while the quote has no modules."""
    # The API always sends every key (null when empty): the published output schema marks them as required
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    by_role: list[RoleCost] | None = None
    direct_cost: int | None = None
    contingency: int | None = None
    margin: int | None = None
    subtotal: int | None = None
    discount: int | None = None
    taxable_base: int | None = None
    vat: int | None = None
    total: int | None = None
    duration_weeks: int | None = None
    payment_milestones: list[Milestone] | None = None
    params: FinanceParams | None = None
